# F1 Dash Setup

This repository has been overhauled to use the `f1-dash` Next.js + Rust stack.

## Components

1.  **Frontend (`dash/`)**: A Next.js application for the UI.
2.  **Live Service (`services/live/`)**: A Rust service that streams F1 data to the frontend via SSE.

## Running the Project

### Prerequisites
- Node.js (v18+)
- Rust (latest stable)

### Replay Mode (Historical Data)

To view the "Previous Car Races Animation" using the provided sample data:

1.  **Start the Live Service in Replay Mode:**

    ```bash
    export REPLAY_PATH="data_samples/2024_Imola_Race"
    export ORIGIN="http://localhost:3000"
    cargo run -p live
    ```

    This will replay the 2024 Imola Race data.

2.  **Start the Frontend:**

    In a separate terminal:

    ```bash
    cd dash
    export NEXT_PUBLIC_LIVE_URL="http://localhost:4000"
    export API_URL="http://localhost:4001"
    npm install
    npm start
    ```

    Open [http://localhost:3000](http://localhost:3000).

### Live Mode

To connect to the real F1 Live Timing feed:

1.  Unset `REPLAY_PATH`.
2.  Run the live service: `cargo run -p live`.
    (Note: This connects to F1 servers and requires an active session or might need authentication configuration in `crates/client`).

## Notes

- The database components (importer, analytics, postgres) are present in the code but require a Postgres/TimescaleDB instance to be running. The frontend has been configured to tolerate the absence of the API service for live views.
