use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use std::time::Duration;
use tokio::sync::mpsc;
use tokio::time::sleep;
use tokio_stream::wrappers::ReceiverStream;
use tracing::{info, error};
use serde_json::Value;
use crate::message::{self, Message};

pub fn replay_file(path_str: String) -> ReceiverStream<Message> {
    let (tx, rx) = mpsc::channel::<Message>(32);
    let path = Path::new(&path_str);
    let path_buf = path.to_path_buf();

    tokio::spawn(async move {
        info!("Starting replay from {:?}", path_buf);

        let mut subscribe_path = path_buf.clone();
        subscribe_path.push("subscribe.txt");

        let mut live_path = path_buf.clone();
        live_path.push("live.txt");

        // 1. Send Initial State
        if let Ok(file) = File::open(&subscribe_path) {
            let reader = BufReader::new(file);
            let mut content = String::new();
            for line in reader.lines() {
                if let Ok(l) = line {
                    content.push_str(&l);
                }
            }

            // Wrap in R
            let wrapper = format!("{{ \"R\": {} }}", content);
            if let Some(msg) = message::parse(wrapper.into()) {
                info!("Sent initial state");
                let _ = tx.send(msg).await;
            } else {
                error!("Failed to parse initial state from subscribe.txt");
            }
        } else {
            error!("Could not open subscribe.txt at {:?}", subscribe_path);
        }

        sleep(Duration::from_secs(2)).await;

        // 2. Stream Updates
        if let Ok(file) = File::open(&live_path) {
            let reader = BufReader::new(file);
            let mut last_time: Option<String> = None;

            for line in reader.lines() {
                if let Ok(l) = line {
                    // undercut-f1 lines are like: {"H":..., "M":"feed", "A":["Category", {Body}, "Timestamp"]}
                    // We need to parse it to extract timestamp for delay, and wrap it for f1-dash parser.

                    let json_line: Value = match serde_json::from_str(&l) {
                        Ok(v) => v,
                        Err(_) => continue,
                    };

                    // Extract timestamp from arguments if present to simulate delay?
                    // undercut-f1 A is [category, data, timestamp?]
                    // Let's just use a fixed delay for now to ensure it runs smooth.
                    sleep(Duration::from_millis(100)).await;

                    // Wrap for f1-dash: { "M": [ line ] }
                    // Re-serialize the line json to string to put inside the wrapper, or construct Value directly.
                    // message::parse takes Utf8Bytes (String).

                    let wrapper = format!("{{ \"M\": [ {} ] }}", l);
                    if let Some(msg) = message::parse(wrapper.into()) {
                        if tx.send(msg).await.is_err() {
                            break;
                        }
                    }
                }
            }
        } else {
            error!("Could not open live.txt at {:?}", live_path);
        }

        info!("Replay finished. Restarting...");
    });

    ReceiverStream::new(rx)
}
