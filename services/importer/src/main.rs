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
                    for driver in drivers { let _ = insert_timing_driver(pool, &driver).await; }
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

// --- MISSING IMPLEMENTATIONS ADDED BELOW ---

async fn save_initial_state(pool: &PgPool, initial: Value) -> Result<(), Error> {
    let state = serde_json::from_value::<State>(initial)?;
    
    // Save Timing Data
    if let Some(timing_data) = &state.timing_data {
        for (nr, driver) in &timing_data.lines {
            // Pass None for lap and update since this is initial state
            if let Some(d) = parse_timing_driver(nr, None, driver, None) {
                 let _ = insert_timing_driver(pool, &d).await;
            }
        }
    }

    // Save Tire Data
    if let Some(timing_app_data) = &state.timing_app_data {
         for (nr, driver) in &timing_app_data.lines {
             if let Some(d) = parse_tire_driver(nr, None, driver, None) {
                 let _ = insert_tire_driver(pool, d).await;
             }
         }
    }
    Ok(())
}

async fn parse_timing_update(state: &State, update: Value) -> Option<Vec<TimingDriver>> {
    let lines = update.get("lines")?.as_object()?;
    let mut drivers = Vec::new();
    
    for (nr, value) in lines {
        if let Some(driver_data) = state.timing_data.as_ref().and_then(|td| td.lines.get(nr)) {
            // Note: We pass None for lap here as logic to extract current lap from state/update is complex
            // and often handled by the database or downstream logic.
            if let Some(d) = parse_timing_driver(nr, None, driver_data, Some(value)) {
                drivers.push(d);
            }
        }
    }
    
    if drivers.is_empty() { None } else { Some(drivers) }
}

async fn parse_tire_update(state: &State, update: Value) -> Option<Vec<TireDriver>> {
    let lines = update.get("lines")?.as_object()?;
    let mut drivers = Vec::new();
    
    for (nr, value) in lines {
        if let Some(driver_data) = state.timing_app_data.as_ref().and_then(|td| td.lines.get(nr)) {
            if let Some(d) = parse_tire_driver(nr, None, driver_data, Some(value)) {
                drivers.push(d);
            }
        }
    }
    
    if drivers.is_empty() { None } else { Some(drivers) }
}
