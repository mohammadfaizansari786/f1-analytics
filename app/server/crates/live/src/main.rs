use axum::{
    extract::ws::{Message, WebSocket, WebSocketUpgrade},
    response::IntoResponse,
    routing::get,
    Router,
};
use futures::{sink::SinkExt, stream::StreamExt};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::broadcast;
use tower_http::cors::CorsLayer;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let (tx, _rx) = broadcast::channel(100);
    let app_state = Arc::new(AppState { tx });

    // Start the simulation loop
    let state_clone = app_state.clone();
    tokio::spawn(async move {
        run_simulation(state_clone).await;
    });

    let app = Router::new()
        .route("/ws", get(ws_handler))
        .with_state(app_state)
        .layer(CorsLayer::permissive());

    let addr = SocketAddr::from(([0, 0, 0, 0], 4000));
    println!("listening on {}", addr);
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

struct AppState {
    tx: broadcast::Sender<String>,
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    axum::extract::State(state): axum::extract::State<Arc<AppState>>,
) -> impl IntoResponse {
    ws.on_upgrade(|socket| handle_socket(socket, state))
}

async fn handle_socket(socket: WebSocket, state: Arc<AppState>) {
    let (mut sender, _receiver) = socket.split();
    let mut rx = state.tx.subscribe();

    while let Ok(msg) = rx.recv().await {
        if sender.send(Message::Text(msg)).await.is_err() {
            break;
        }
    }
}

// --- Simulation Logic ---

#[derive(Serialize, Clone)]
struct Position {
    x: i32,
    y: i32,
    z: i32,
}

#[derive(Serialize, Clone)]
struct DriverData {
    driver_number: u32,
    position: Position,
    speed: u32,
    gear: u8,
    rpm: u32,
    throttle: u8,
    brake: u8,
}

#[derive(Serialize, Clone)]
struct Payload {
    pos: std::collections::HashMap<u32, Position>,
    telemetry: std::collections::HashMap<u32, DriverData>,
}

fn get_track_points() -> Vec<(i32, i32)> {
    // Simplified Red Bull Ring approx
    vec![
        (0, 0),         // Start/Finish
        (2000, 0),      // Straight
        (3000, 500),    // Turn 1 Entry
        (3500, 2000),   // Turn 1 Apex/Exit (Uphill)
        (3000, 3000),   // Straight to T3
        (1000, 3500),   // T3 hairpin area
        (0, 3000),      // Downhill
        (-2000, 2000),  // Infield
        (-3000, 1000),  // Final corners
        (0, 0),         // Finish
    ]
}

fn interpolate(p1: (i32, i32), p2: (i32, i32), t: f64) -> (i32, i32) {
    let x = p1.0 as f64 + (p2.0 as f64 - p1.0 as f64) * t;
    let y = p1.1 as f64 + (p2.1 as f64 - p1.1 as f64) * t;
    (x as i32, y as i32)
}

async fn run_simulation(state: Arc<AppState>) {
    let track = get_track_points();
    let total_segments = track.len() - 1;

    // Each driver has a "progress" (0.0 to total_segments.0)
    let drivers_ids = vec![1, 11, 16, 55, 44, 63, 4, 81];
    let mut driver_progress: std::collections::HashMap<u32, f64> = std::collections::HashMap::new();

    // Initialize random start positions
    for (i, &id) in drivers_ids.iter().enumerate() {
        driver_progress.insert(id, i as f64 * 0.5);
    }

    loop {
        let mut positions = std::collections::HashMap::new();
        let mut telemetry = std::collections::HashMap::new();

        for &id in &drivers_ids {
            let prog = driver_progress.get_mut(&id).unwrap();
            *prog += 0.05; // Move forward
            if *prog >= total_segments as f64 {
                *prog = 0.0;
            }

            let seg_idx = prog.floor() as usize;
            let t = *prog - seg_idx as f64;

            let p1 = track[seg_idx];
            let p2 = track[seg_idx + 1];

            let (x, y) = interpolate(p1, p2, t);
            let pos = Position { x, y, z: 0 };

            positions.insert(id, pos.clone());

            // Fake telemetry
            let speed = (200.0 + (t * 100.0).sin() * 50.0) as u32;
            telemetry.insert(id, DriverData {
                driver_number: id,
                position: pos,
                speed,
                gear: (speed / 40).min(8) as u8,
                rpm: 10000 + (speed * 10),
                throttle: if speed > 100 { 100 } else { 50 },
                brake: if speed < 100 { 50 } else { 0 },
            });
        }

        let payload = Payload {
            pos: positions,
            telemetry,
        };

        if let Ok(msg) = serde_json::to_string(&payload) {
             let _ = state.tx.send(msg);
        }

        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    }
}
