use anyhow::Error;
use dotenvy::dotenv;
use serde_json::Value;
use sqlx::PgPool;
use tracing::{info, trace};
use tracing_subscriber::{fmt, layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};
use client::message::Message;
use timescale::{app_timing::{insert_tire_driver, TireDriver}, init_timescaledb, timing::{insert_timing_driver, TimingDriver}};
use models::State;
use parsers::{parse_timing_driver, parse_tire_driver};

mod models;
mod parsers;

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    let _ = dotenv();
    tracing_subscriber::registry().with(fmt::layer()).with(EnvFilter::from_default_env()).init();
    info!("starting importer service");

    let pool = init_timescaledb(true).await?;
    let stream = client::manage();
    let (tx, rx) = client::broadcast(stream);
    let state = client::keep_state(rx);
    let mut message_rx = tx.subscribe();

    while let Ok(message) = message_rx.recv().await {
        match message {
            Message::Updates(updates) => {
                trace!(?updates, "recived updates, saving");
                let current_state = state.lock().unwrap().clone();
                let _ = parse_update(&pool, current_state, updates).await;
            }
            Message::Initial(initial) => {
                trace!(?initial, "recived initial, saving");
                let _ = save_initial_state(&pool, initial).await;
            }
        }
    }
    Ok(())
}

async fn parse_update(pool: &PgPool, state: Value, updates: Vec<(String, Value)>) -> Result<(), Error> {
    let state = serde_json::from_value::<State>(state)?;
    for (topic, update) in updates {
        match &topic[..] {
            "timingData" => {
                if let Some(drivers) = parse_timing_update(&state, update).await {
                    for driver in drivers { let _ = insert_timing_driver(pool, driver).await; }
                }
            }
            "timingAppData" => {
                if let Some(drivers) = parse_tire_update(&state, update).await {
                    for driver in drivers { let _ = insert_tire_driver(pool, driver).await; }
                }
            }
            _ => {}
        }
    }
    Ok(())
}
// Include parse_timing_update, parse_tire_update, save_initial_state helper functions here (as seen in original file)
