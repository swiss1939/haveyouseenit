# Have You Seen It? - Movie Tracker (Alpha v1.0)

![Have You Seen It? Interface](https://i.imgur.com/gO9qB1m.gif)
*A simple, fast, and fun way to track the movies you've watched.*

## Overview

Have You Seen It? is a Django-based web application designed to help users quickly build a library of the movies they have seen. It features a modern, mobile-friendly swipe interface (similar to Tinder) for rating movies, powered by data from The Movie Database (TMDb).

The core philosophy is to make movie logging fast and enjoyable by presenting users with one movie at a time. The movie selection is not purely random; it uses a weighted algorithm biased towards more popular and well-known films to improve the user experience.

## Core Features (v1.0)

-   **User Authentication:** Secure user signup, login, and logout functionality.
-   **Swipe Interface:** Rate movies with a simple "Yes" (seen) or "No" (not seen) swipe, powered by Hammer.js.
-   **Weighted Randomization:** The movie suggestion engine is weighted by box office revenue, ensuring users are more likely to see popular, recognizable films.
-   **Live "Movies Seen" Counter:** A dynamic counter in the header animates and updates in real-time with every "seen" swipe.
-   **Persistent Filtering:** Users can filter the movie queue by **Genre** and by a text search for **Actors, Directors, Producers, or Cinematographers**. Filters remain active between swipes.
-   **User Profile Dashboard:** A simple page that displays the user's total number of seen movies and other account details.
-   **Custom Django Admin:** A highly customized admin panel for easy data browsing, including performance optimizations for models with many relationships.
-   **Dockerized Environment:** The entire application is containerized with Docker and Docker Compose for easy and reproducible setup.
-   **Robust Data Ingestion:** Includes management commands to populate the database with movie data from the TMDb API, including backfilling of detailed stats and credits.

## Technology Stack

-   **Backend:** Python, Django
-   **Database:** PostgreSQL (configured in Docker), SQLite (for initial development)
-   **Frontend:** HTML, Bootstrap 5, Hammer.js
-   **DevOps:** Docker, Docker Compose

## Setup and Installation

To run this project locally, you will need Docker and Docker Compose installed.

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd haveyouseenit
    ```

2.  **Configure Environment Variables:**
    Rename the `.env.example` file to `.env` (or create a new `.env` file) and add your TMDB API key:
    ```
    # haveyouseenit/.env
    TMDB_API_KEY=your_actual_tmdb_api_key_here
    ```

3.  **Build and Run the Containers:**
    ```bash
    docker-compose up --build -d
    ```

4.  **Run Database Migrations:**
    Apply the initial database schema.
    ```bash
    docker-compose exec web python manage.py migrate
    ```

5.  **Ingest Movie Data:**
    Run the management commands to populate the database.
    ```bash
    # Ingest a base set of popular movies (first)
    docker-compose exec web python manage.py ingest_tmdb_popular

    # Backfill detailed stats (revenue, runtime) and credits for the ingested movies
    docker-compose exec web python manage.py backfill_stats
    ```
    *Note: For a more comprehensive database, you can also run `ingest_tmdb_year`.*

6.  **Create a Superuser (Optional):**
    To access the admin panel (`/admin`), create a superuser.
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

The application will be available at `http://localhost:9000`.

---

## Pending Fixes & Future Features

This section outlines the next steps for development.

### High-Priority Fixes

-   **Improve Filter UI/UX:**
    -   **Goal:** Create a "buttonless" interface for the header filters.
    -   **Details:**
        1.  Remove the explicit "Filter" and "Clear" buttons.
        2.  The genre dropdown should auto-submit and reload the movie queue on change.
        3.  The person search bar should submit when the user presses "Enter".
        4.  Implement custom, in-field "X" buttons that appear only when a filter is active, allowing users to clear a specific filter with a single click.

### Next Major Feature

-   **Advanced Person Filtering by Role:**
    -   **Goal:** Allow users to filter by a specific person *in a specific role*.
    -   **Details:**
        1.  Convert the person search bar into a dynamic, autocomplete field. As the user types a name (e.g., "John Carpenter"), an API will provide a list of matching people.
        2.  When the user selects a person, a second dropdown or suggestion list should appear, populated by another API call that fetches all the roles that person has in the database (e.g., "Director", "Producer", "Actor").
        3.  The final filter will be applied based on both the person's ID and their selected role, resulting in a much more precise movie queue.
