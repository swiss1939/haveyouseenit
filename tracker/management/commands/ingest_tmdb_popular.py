# tracker/management/commands/ingest_tmdb_data.py
import time
import requests
import os
import sys 
from django.core.management.base import BaseCommand
from tracker.models import Movie, Genre
from django.db import transaction
from django.db.utils import IntegrityError, DatabaseError
from tqdm import tqdm # <-- NEW IMPORT

# --- Configuration ---
TMDB_API_KEY = os.getenv("TMDB_API_KEY") 
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# --- API Rate Limit Safety ---
REQUEST_DELAY = 0.25 


class Command(BaseCommand):
    help = 'Fetches movies from TMDb. Displays a progress bar and time estimate.'

    tmdb_genre_map = {} 

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='backfill',
            help='Specify the ingestion mode: "backfill" (max 500 pages) or "daily" (pages 1-3 of Now Playing).'
        )

    def _get_or_fetch_genres(self):
        """Fetches the official TMDb genre list and populates the local Genre table."""
        if self.tmdb_genre_map:
            return True

        self.stdout.write(self.style.NOTICE("Fetching official TMDb Genre list..."))
        url = f"{TMDB_BASE_URL}/genre/movie/list?api_key={TMDB_API_KEY}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"FATAL: Could not fetch genres from TMDb: {e}"))
            return False

        with transaction.atomic():
            for genre_data in data.get('genres', []):
                genre_obj, created = Genre.objects.get_or_create(
                    name=genre_data['name']
                )
                self.tmdb_genre_map[genre_data['id']] = genre_obj
                
            self.stdout.write(self.style.SUCCESS(f"Successfully loaded {len(self.tmdb_genre_map)} unique genres."))
            time.sleep(REQUEST_DELAY) 
        return True

    def _process_page(self, url, page, max_pages):
        """Helper function to handle API calls, rate limits, and database insertion for a single page."""
        
        # --- API Call and Rate Limit Handling ---
        try:
            response = requests.get(url)

            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', 5) 
                # This needs to be handled outside the tqdm loop to pause the whole process cleanly
                raise requests.exceptions.HTTPError(f"Rate limit hit. Retry-After: {retry_after}")

            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f'Failed to fetch page {page}. Status: {response.status_code}. Skipping page.'))
                if response.status_code in [401, 403]:
                    self.stdout.write(self.style.ERROR('FATAL: Check your TMDB_API_KEY. Breaking process.'))
                    sys.exit(1) 
                return 0, False, 0 
            
            data = response.json()

        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Connection error on page {page}: {e}. Skipping.'))
            time.sleep(1)
            return 0, False, 0
        except requests.exceptions.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Failed to decode JSON response for page {page}. Skipping page.'))
            return 0, False, 0
        except requests.exceptions.HTTPError as e:
            # Re-raise the HTTP error to be caught by the main loop's try/except
            raise e
        
        # Determine max_pages (only from the first page)
        total_pages = data.get('total_pages', max_pages) if page == 1 else max_pages
        
        if not isinstance(data.get('results'), list) or not data.get('results'):
             self.stdout.write(self.style.WARNING(f"No movie results found for page {page}. Skipping."))
             return 0, False, total_pages
        
        new_movies_count = 0
        
        # --- Database Insertion ---
        try:
            with transaction.atomic():
                for movie_data in data.get('results', []):
                    tmdb_id = movie_data.get('id')
                    
                    try:
                        # Skip if already exists (ensures continuation)
                        if Movie.objects.filter(tmdb_id=tmdb_id).exists(): 
                            continue 
                        
                        # Data Sanitization and Conversion
                        release_date_str = movie_data.get('release_date', '')
                        release_year = int(release_date_str.split('-')[0]) if release_date_str and release_date_str.split('-')[0].isdigit() else None
                        
                        if not release_year:
                            continue

                        movie = Movie.objects.create(
                            title=movie_data.get('title'),
                            release_year=release_year,
                            tmdb_id=tmdb_id,
                            plot_summary=movie_data.get('overview'),
                            poster_url=f"https://image.tmdb.org/t/p/w500{movie_data.get('poster_path')}" if movie_data.get('poster_path') else None,
                            imdb_id=None,
                        )
                        
                        for genre_id in movie_data.get('genre_ids', []):
                            genre_obj = self.tmdb_genre_map.get(genre_id)
                            if genre_obj:
                                movie.genre.add(genre_obj)
                        
                        new_movies_count += 1
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Record Error for TMDb ID {tmdb_id}: {type(e).__name__} - {e}. Skipping record."))
                        continue 
            
            return new_movies_count, True, total_pages
        
        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f"FATAL DATABASE ERROR on page {page}. Aborting command. Error: {e}"))
            sys.exit(1)


    def handle(self, *args, **options):
        mode = options['mode'].lower()

        if not TMDB_API_KEY:
            self.stdout.write(self.style.ERROR('TMDB_API_KEY environment variable not set. Aborting.'))
            return
            
        if not self._get_or_fetch_genres():
            self.stdout.write(self.style.ERROR("Genre loading failed. Aborting movie ingestion."))
            return

        # Determine the page range and max page cap based on mode
        if mode == 'backfill':
            self.stdout.write(self.style.NOTICE("Running BACKFILL Mode (Max 500 pages of Popular movies)..."))
            base_query_url = f"{TMDB_BASE_URL}/movie/popular?api_key={TMDB_API_KEY}&page="
            start_page = 1
            max_page_cap = 500
        elif mode == 'daily':
            self.stdout.write(self.style.NOTICE("Running DAILY UPDATE Mode (First 3 pages of Now Playing)..."))
            base_query_url = f"{TMDB_BASE_URL}/movie/now_playing?api_key={TMDB_API_KEY}&page="
            start_page = 1
            max_page_cap = 3 # Only check the first few pages for new releases
        else:
            self.stdout.write(self.style.ERROR(f'Invalid mode: {options["mode"]}. Use "backfill" or "daily".'))
            return

        total_new_movies = 0
        total_processed_pages = 0
        
        # --- NEW: Get the total page count dynamically for the progress bar ---
        # Run a quick check on page 1 to get the actual total_pages from TMDb
        self.stdout.write(self.style.NOTICE("Determining total pages for progress bar..."))
        _, _, actual_total_pages = self._process_page(base_query_url + str(start_page), start_page, max_page_cap)
        
        # Cap the max loop pages at the determined limit or the hard cap (500)
        final_page_limit = min(actual_total_pages, max_page_cap) if actual_total_pages > 0 else max_page_cap
        
        self.stdout.write(self.style.NOTICE(f"Processing {final_page_limit} pages with a {REQUEST_DELAY}s delay."))
        
        
        # --- NEW: Use tqdm to wrap the main loop ---
        # tqdm displays the progress, elapsed time, and estimated time remaining (ETA)
        page_range = range(start_page, final_page_limit + 1)
        
        with tqdm(page_range, desc="Ingestion Progress", unit="page", file=sys.stdout) as t_bar:
            for page in t_bar:
                url = base_query_url + str(page)
                
                try:
                    count, success, _ = self._process_page(url, page, final_page_limit)
                    total_new_movies += count
                    
                    if not success:
                        # If a non-fatal error occurred (like empty results), continue to next page
                        pass 
                    
                    # Update tqdm description with current stats
                    t_bar.set_postfix_str(f"New: {total_new_movies}")
                    
                except requests.exceptions.HTTPError as e:
                    # Handle the specific rate limit error raised from _process_page
                    retry_after = int(e.args[0].split(':')[-1].strip())
                    self.stdout.write(self.style.WARNING(f"\n[RATE LIMIT HIT] Pausing for {retry_after} seconds..."))
                    time.sleep(retry_after + 1)
                    t_bar.update(-1) # Decrement the counter to re-process the current page
                    continue
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"\n[FATAL ERROR] Unknown error on page {page}: {e}"))
                    sys.exit(1)
                
                # --- IMPLEMENT THE REQUIRED DELAY ---
                time.sleep(REQUEST_DELAY) 

        self.stdout.write(self.style.SUCCESS(f'\n--- Ingestion Complete ---'))
        self.stdout.write(self.style.SUCCESS(f'Total new movies added in {mode.upper()} mode: {total_new_movies}'))
