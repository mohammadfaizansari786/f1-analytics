use std::sync::Arc;
use std::net::SocketAddr;
use axum::{extract::{ws::{Message, WebSocket}, State, WebSocketUpgrade}, response::Response, routing::get, Router};
use futures::{SinkExt, StreamExt};
use tokio::sync::{broadcast, mpsc, Mutex};
use tracing::{error, info};
use tokio::net::TcpListener;

pub struct AppState { tx: broadcast::Sender<String>, mpsc_tx: mpsc::Sender<()> }

fn addr() -> SocketAddr {
    std::env::var("SIMULATOR_ADDRESS")
        .unwrap_or_else(|_| "0.0.0.0:8000".to_string())
        .parse()
        .expect("invalid SIMULATOR_ADDRESS")
}

pub async fn init(tx: broadcast::Sender<String>, mpsc_tx: mpsc::Sender<()>) {
    let app_state = Arc::new(AppState { tx, mpsc_tx });
    let app = Router::new().route("/ws", get(handle_http)).with_state(app_state.clone());
    let listener = TcpListener::bind(addr()).await.expect("failed to bind to port");
    info!("serving ws simulator on {}", addr());
    axum::serve(listener, app).await.expect("failed to serve http server");
}

async fn handle_http(ws: WebSocketUpgrade, State(state): State<Arc<AppState>>) -> Response {
    ws.on_upgrade(|socket| handle_ws(socket, state))
}

async fn handle_ws(socket: WebSocket, state: Arc<AppState>) {
    let mut reader_rx = state.tx.subscribe();
    // notify a watcher that a client connected; don't block on send
    if let Err(e) = state.mpsc_tx.clone().try_send(()) {
        error!("failed to notify on client connect: {}", e);
    }
    info!("client connected to ws simulator");

    let (tx, mut rx) = socket.split();
    // wrap the sink in an Arc<Mutex<...>> so both branches can send without
    // borrowing the underlying sink mutably in two different async blocks
    let tx = Arc::new(Mutex::new(tx));

    tokio::select! {
        // forward broadcast messages to the websocket client
        _ = async {
            while let Ok(msg) = reader_rx.recv().await {
                let mut tx_lock = tx.lock().await;
                if let Err(e) = tx_lock.send(Message::text(msg)).await {
                    error!("failed to send message: {}", e);
                    break;
                }
            }
        } => {}

        // handle incoming websocket messages
        _ = async {
            while let Some(Ok(msg)) = rx.next().await {
                match msg {
                    Message::Close(_) => {
                        info!("received close");
                        break;
                    }
                    Message::Ping(payload) => {
                        // respond with Pong to keep the connection healthy
                        let mut tx_lock = tx.lock().await;
                        if let Err(e) = tx_lock.send(Message::Pong(payload)).await {
                            error!("failed to send pong: {}", e);
                            break;
                        }
                    }
                    _ => {
                        // ignore other message types (Text/Binary/Pong)
                    }
                }
            }
        } => {}
    }

    info!("client disconnected from ws simulator");
}
