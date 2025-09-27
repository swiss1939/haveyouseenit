# Have You Seen It? - Movie Tracker (Alpha v0.01)

*A simple, fast, and fun way to track the movies you've watched.*

## Overview

Have You Seen It? is a Django-based web application designed to help users quickly build a library of the movies they have seen. It features a modern, mobile-friendly swipe interface for rating movies, powered by data from The Movie Database (TMDb).

The core philosophy is to make movie logging fast and enjoyable by presenting users with one movie at a time. The movie selection is not purely random; it uses a weighted algorithm biased towards more popular and well-known films to improve the user experience.

## Core Features (v0.01)

-   **User Accounts:** Simple and secure signup, login, and logout.
-   **Swipe to Rate:** Quickly rate movies as "Seen" or "Not Seen" with a fun, intuitive swipe interface.
-   **Smart Suggestions:** The movie queue is intelligently weighted to show you more popular and recognizable films, not just obscure ones.
-   **Live Seen Counter:** Watch your "Movies Seen" count animate and update in real-time as you rate.
-   **Powerful Filtering:** Filter the movie queue by Genre or search for a specific Person (e.g., actor, director).
-   **Profile Dashboard:** View your total movie count and account details on a personal dashboard.

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
    Create a `.env` file in the root directory and add your TMDB API key:
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
