# tracker/management/commands/ingest_tmdb_year.py
import time
import requests
import os
import sys 
from django.core.management.base import BaseCommand
from tracker.models import Movie, Genre
from django.db import transaction, DatabaseError
from tqdm import tqdm # For progress bar

# --- Configuration ---
TMDB_API_KEY = os.getenv("TMDB_API_KEY") 
TMDB_BASE_URL = "https://api.themoviedb.org/3"
REQUEST_DELAY = 0.25 

# Set the year range for comprehensive ingestion
START_YEAR = 1900 
CURRENT_YEAR = time.localtime().tm_year # Gets the current year dynamically
# Max pages TMDb allows per query
MAX_PAGE_CAP = 500 


class Command(BaseCommand):
    help = 'Comprehensive backfill: Fetches all discoverable movies by iterating through each year (1900-Present).'

    tmdb_genre_map = {} 

    def _get_or_fetch_genres(self):
        # ... (Same _get_or_fetch_genres logic as before) ...
        # [NOTE: Since this is the same helper function, ensure the full logic is copied here]
        # For brevity, this comment stands in for the correct function logic.
        
        # --- START OF _get_or_fetch_genres LOGIC ---
        if self.tmdb_genre_map: return True
        self.stdout.write(self.style.NOTICE("Fetching official TMDb Genre list..."))
        url = f"{TMDB_BASE_URL}/genre/movie/list?api_key={TMDB_API_KEY}"
        try:
            response = requests.get(url); response.raise_for_status(); data = response.json()
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"FATAL: Could not fetch genres from TMDb: {e}")); return False
        with transaction.atomic():
            for genre_data in data.get('genres', []):
                genre_obj, _ = Genre.objects.get_or_create(name=genre_data['name'])
                self.tmdb_genre_map[genre_data['id']] = genre_obj
            self.stdout.write(self.style.SUCCESS(f"Successfully loaded {len(self.tmdb_genre_map)} unique genres.")); time.sleep(REQUEST_DELAY) 
        return True
        # --- END OF _get_or_fetch_genres LOGIC ---


    def _process_page(self, url, page):
        """Helper function to handle API calls, rate limits, and database insertion for a single page."""
        
        # --- API Call and Error/Rate Limit Handling (Simplified for snippet, same as previous) ---
        try:
            response = requests.get(url)
            if response.status_code == 429:
                raise requests.exceptions.HTTPError(f"Rate limit hit. Retry-After: {response.headers.get('Retry-After', 5)}")
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f'Failed fetch. Status: {response.status_code}. Skipping.'))
                if response.status_code in [401, 403]: sys.exit(1)
                return 0, 0
            
            data = response.json()
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            # Handle rate limit and other requests errors gracefully by returning 0
            return 0, 0
        except requests.exceptions.JSONDecodeError:
            return 0, 0
            
        if not isinstance(data.get('results'), list) or not data.get('results'):
             return 0, 0
        
        total_pages = min(data.get('total_pages', 0), MAX_PAGE_CAP) # Cap total pages at 500
        new_movies_count = 0
        
        # --- Database Insertion (Same logic as before) ---
        try:
            with transaction.atomic():
                for movie_data in data.get('results', []):
                    tmdb_id = movie_data.get('id')
                    try:
                        if Movie.objects.filter(tmdb_id=tmdb_id).exists(): continue 
                        
                        release_date_str = movie_data.get('release_date', '')
                        release_year = int(release_date_str.split('-')[0]) if release_date_str and release_date_str.split('-')[0].isdigit() else None
                        if not release_year: continue

                        movie = Movie.objects.create(
                            title=movie_data.get('title'), release_year=release_year, tmdb_id=tmdb_id, 
                            plot_summary=movie_data.get('overview'),
                            poster_url=f"https://image.tmdb.org/t/p/w500{movie_data.get('poster_path')}" if movie_data.get('poster_path') else None,
                            imdb_id=None,
                        )
                        for genre_id in movie_data.get('genre_ids', []):
                            genre_obj = self.tmdb_genre_map.get(genre_id)
                            if genre_obj: movie.genre.add(genre_obj)
                        
                        new_movies_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Record Error TMDb ID {tmdb_id}: {type(e).__name__} - {e}. Skipping."))
                        continue 
            
            return new_movies_count, total_pages
        
        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f"FATAL DB ERROR: {e}. Aborting."))
            sys.exit(1)


    def handle(self, *args, **options):
        if not TMDB_API_KEY:
            self.stdout.write(self.style.ERROR('TMDB_API_KEY not set. Aborting.'))
            return
            
        if not self._get_or_fetch_genres():
            self.stdout.write(self.style.ERROR("Genre loading failed. Aborting movie ingestion."))
            return

        total_new_movies = 0
        
        # --- Outer Loop: Iterate through each year ---
        # The range is reversed so we ingest the newest, most relevant movies first
        year_range = range(CURRENT_YEAR, START_YEAR - 1, -1)
        
        with tqdm(year_range, desc="Overall Year Progress", unit="year", file=sys.stdout) as year_bar:
            for year in year_bar:
                year_bar.set_description(f"Processing Year {year}")
                base_query_url = f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&primary_release_year={year}&page="
                
                # --- Inner Loop: Page-by-page ingestion for the current year ---
                current_page = 1
                total_pages_for_year = MAX_PAGE_CAP # Assume max cap initially

                while current_page <= total_pages_for_year:
                    url = base_query_url + str(current_page)
                    
                    try:
                        count, new_total_pages = self._process_page(url, current_page)
                        
                        # Only update the total page count if it's the first page
                        if current_page == 1 and new_total_pages > 0:
                            total_pages_for_year = new_total_pages
                            self.stdout.write(f"\nYear {year}: Found {new_total_pages} pages ({new_total_pages * 20} movies).")
                        
                        total_new_movies += count
                        current_page += 1
                        
                        year_bar.set_postfix_str(f"New: {total_new_movies} | Page: {current_page-1}/{total_pages_for_year}")

                    except requests.exceptions.HTTPError as e:
                        retry_after = int(e.args[0].split(':')[-1].strip())
                        self.stdout.write(self.style.WARNING(f"\n[RATE LIMIT HIT] Pausing for {retry_after} seconds. Retrying page {current_page}."))
                        time.sleep(retry_after + 1)
                        continue # Stay on the current page
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"\n[FATAL ERROR] Unknown error on year {year}, page {current_page}: {e}"))
                        sys.exit(1)
                    
                    # --- IMPLEMENT THE REQUIRED DELAY ---
                    time.sleep(REQUEST_DELAY) 

        self.stdout.write(self.style.SUCCESS(f'\n--- Comprehensive Backfill Complete ---'))
        self.stdout.write(self.style.SUCCESS(f'Total new movies added: {total_new_movies}'))
