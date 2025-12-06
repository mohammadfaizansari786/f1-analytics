use std::{env, fs::File, io::{LineWriter, Write}};
use tokio_stream::StreamExt;
use tracing::{debug, error, info, level_filters::LevelFilter, warn};
// FIX: Removed "use client;" warning

#[tokio::main]
async fn main() {
    init_logs();
    let path = match env::args().nth(1) {
        Some(path) => path,
        None => { error!(r#"no path provided, usage "saver <path>""#); return; }
    };
    let path = std::path::Path::new(&path);
    if path.exists() { error!("file already exists at path {}", path.display()); return; }
    let mut file = match File::create(path) {
        Ok(file) => LineWriter::new(file),
        Err(e) => { error!("failed to create file at path {}", e); return; }
    };
    info!("saving socket data to path {}", path.display());
    let mut stream = match client::init().await {
        Ok(stream) => stream,
        Err(e) => { error!("failed to init client {}", e); return; }
    };
    while let Some(Ok(msg)) = stream.next().await {
        match msg {
            client::tungstenite::Message::Text(txt) => {
                debug!("received message: {}", txt);
                if let Err(e) = writeln!(file, "{}", txt) { error!("failed to write message to file {}", e); }
            }
            client::tungstenite::Message::Close(_) => { error!("connection got closed by server"); break; }
            _ => warn!("unhandled message, probably binary, ping or pong"),
        }
    }
    if let Err(e) = file.flush() { error!("failed to flush file {}", e); }
    info!("done");
}

fn init_logs() {
    let env_filter = tracing_subscriber::EnvFilter::builder()
        .with_default_directive(LevelFilter::INFO.into())
        .with_env_var("RUST_LOG")
        .from_env_lossy();
    tracing_subscriber::fmt().with_env_filter(env_filter).init();
}
