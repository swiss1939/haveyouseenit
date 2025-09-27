# tracker/management/commands/backfill_stats.py
import time
import requests
import os
import sys
from django.core.management.base import BaseCommand
from tracker.models import Movie, Actor, Cinematographer, Director, Producer # NEW IMPORTS
from django.db import transaction, IntegrityError
from tqdm import tqdm 

# --- Configuration ---
TMDB_API_KEY = os.getenv("TMDB_API_KEY") 
TMDB_BASE_URL = "https://api.themoviedb.org/3"
REQUEST_DELAY = 0.25 


class Command(BaseCommand):
    help = 'Fetches detailed stats (Revenue, Runtime) and Credits (All Personnel) for existing movies.'

    def _fetch_details_and_credits(self, tmdb_id):
        """Fetches both details and credits in a single request using append_to_response."""
        
        # Use append_to_response to get credits and external IDs in one efficient API call
        url = (
            f"{TMDB_BASE_URL}/movie/{tmdb_id}?"
            f"api_key={TMDB_API_KEY}&append_to_response=credits"
        )
        
        response = requests.get(url)
        response.raise_for_status()
        return response.json()


    def handle(self, *args, **options):
        if not TMDB_API_KEY:
            self.stdout.write(self.style.ERROR('TMDB_API_KEY not set. Aborting.'))
            return
            
        # Select movies that haven't been processed for credits/details yet 
        movies_to_process = Movie.objects.filter(actors__isnull=True).distinct()
        total_movies = movies_to_process.count()

        if total_movies == 0:
            self.stdout.write(self.style.NOTICE("No new movies found requiring stats or credit backfill. Exiting."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {total_movies} movies to backfill stats and credits for."))
        
        # Use tqdm for progress bar and time estimate
        with tqdm(movies_to_process, desc="Backfilling Stats", unit="movie", file=sys.stdout) as t_bar:
            for movie in t_bar:
                tmdb_id = movie.tmdb_id
                t_bar.set_postfix_str(f"Movie: {movie.title[:30]}...")

                try:
                    # 1. Fetch data from TMDb
                    data = self._fetch_details_and_credits(tmdb_id)

                    with transaction.atomic():
                        # 2. Update core Movie model fields (Revenue, Runtime, IMDb ID)
                        movie.revenue = data.get('revenue', 0)
                        movie.runtime_minutes = data.get('runtime')
                        movie.imdb_id = data.get('imdb_id')
                        movie.save()

                        # 3. Process Credits (Cast and Crew)
                        credits = data.get('credits', {})
                        
                        # Process Actors (Top 10)
                        for cast_member in credits.get('cast', [])[:10]:
                            actor_obj, _ = Actor.objects.get_or_create(
                                tmdb_id=cast_member['id'],
                                defaults={'name': cast_member['name']}
                            )
                            movie.actors.add(actor_obj)

                        # Process Crew (Directors, Producers, Cinematographers)
                        for crew_member in credits.get('crew', []):
                            job = crew_member.get('job')
                            person_tmdb_id = crew_member['id']
                            person_name = crew_member['name']

                            # Process Directors
                            if job == 'Director':
                                director_obj, _ = Director.objects.get_or_create(
                                    tmdb_id=person_tmdb_id,
                                    defaults={'name': person_name}
                                )
                                movie.directors.add(director_obj)
                                
                            # Process Producers
                            if job == 'Producer':
                                producer_obj, _ = Producer.objects.get_or_create(
                                    tmdb_id=person_tmdb_id,
                                    defaults={'name': person_name}
                                )
                                movie.producers.add(producer_obj)
                                
                            # Process Cinematographer
                            if job in ['Director of Photography', 'Cinematographer']:
                                cinematographer_obj, _ = Cinematographer.objects.get_or_create(
                                    tmdb_id=person_tmdb_id,
                                    defaults={'name': person_name}
                                )
                                movie.cinematographers.add(cinematographer_obj)
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        self.stdout.write(f"\n[Warning] Movie {tmdb_id} not found on TMDb. Skipping.")
                    elif e.response.status_code == 429:
                        retry_after = int(e.response.headers.get('Retry-After', 5))
                        self.stdout.write(self.style.WARNING(f"\n[RATE LIMIT HIT] Pausing for {retry_after}s. Retrying..."))
                        time.sleep(retry_after + 1)
                        t_bar.update(-1) 
                        continue 
                    else:
                        self.stdout.write(self.style.ERROR(f"\n[Error] API error for {movie.title}: {e}"))
                except IntegrityError as e:
                    self.stdout.write(self.style.ERROR(f"\n[Error] Integrity error for {movie.title}: {e}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"\n[Error] General error for {movie.title}: {e}"))
                
                # --- IMPLEMENT THE REQUIRED DELAY ---
                time.sleep(REQUEST_DELAY) 

        self.stdout.write(self.style.SUCCESS("\nCredit and Stats backfill complete!"))
