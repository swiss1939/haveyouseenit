# Have You Seen It? - Movie Tracker (Alpha v0.01)

*A simple, fast, and fun way to track the movies you've watched.*

## Overview

Have You Seen It? is a Django-based web application designed to help users quickly build a library of the movies they have seen. It features a modern, mobile-friendly swipe interface for rating movies, powered by data from The Movie Database (TMDb).

The core philosophy is to make movie logging fast and enjoyable by presenting users with a random selection of movies, one at a time.

## Core Features (v0.01)

-   **User Accounts:** Simple and secure signup, login, and logout.
-   **Swipe to Rate:** Quickly rate movies as "Seen" or "Not Seen" with a fun, intuitive swipe interface.
-   **Random Movie Suggestions:** Discover and rate movies from a randomized queue.
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

---

## Current Development Status (`feature/social-and-invitecodes`)

This section outlines the progress and pending tasks for the social and invite code system.

### Completed Functionality:

-   **Data Models:** `InviteCode` and `Friendship` models have been created and migrated.
-   **Invite-Only Signup:** The user creation form now requires a valid, unused invite code.
-   **Auto-Friending:** Users who sign up via an invite code are automatically friended with the inviter.
-   **Profile Page Structure:** The profile page is a single, centered card that integrates all social features.
-   **Friend Management:**
    -   Users can send friend requests from their profile page.
    -   Users can accept/decline incoming requests from their own profile page.

### **In Progress / Next Tasks:**

-   **1. Fix Contextual Action Buttons on Profiles (High Priority):**
    -   **Goal:** When viewing another user's profile, the page should display the correct action button based on the friendship status.
    -   **Current Bug:** If user B has sent a friend request to user A, when user A views user B's profile, it incorrectly shows the public view instead of the "Accept/Decline Request" buttons.

-   **2. Upgrade Search Functionality:**
    -   **Goal:** Convert the static, page-reloading search forms (both in the header and on the profile page) into a dynamic, modern autocomplete experience.
    -   **Details:**
        a.  **Dynamic Loading:** Use JavaScript and a backend API to fetch and display search results instantly without a full page reload.
        b.  **Autocomplete UI:** The search fields should show a dropdown list of suggestions as the user types.
        c.  **Inexact Matching:** The search logic should be upgraded to return *similar* matches (handling typos), not just exact ones. For the production environment, this will be implemented using PostgreSQL's Trigram Similarity.

---

### Next Major Feature

-   **Advanced Person Filtering by Role:**
    -   **Goal:** Allow users to filter by a specific person *in a specific role*.
    -   **Details:**
        1.  Convert the person search bar into a dynamic, autocomplete field. As the user types a name (e.g., "John Carpenter"), an API will provide a list of matching people.
        2.  When the user selects a person, a second dropdown or suggestion list should appear, populated by another API call that fetches all the roles that person has in the database (e.g., "Director", "Producer", "Actor").
        3.  The final filter will be applied based on both the person's ID and their selected role, resulting in a much more precise movie queue.
