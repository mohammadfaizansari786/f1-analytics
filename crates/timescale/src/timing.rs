use sqlx::{PgPool, Row};
use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone)]
pub struct TimingDriver {
    pub nr: String,
    pub lap: Option<i32>,
    pub gap: i64,
    pub leader_gap: i64,
    pub laptime: i64,
    pub sector_1: i64,
    pub sector_2: i64,
    pub sector_3: i64,
}

pub async fn insert_timing_driver(pool: &PgPool, driver: &TimingDriver) -> Result<()> {
    sqlx::query(
        r#"insert into timing_driver (nr, lap, gap, leader_gap, laptime, sector_1, sector_2, sector_3)
        values ($1, $2, $3, $4, $5, $6, $7, $8)"#
    )
    .bind(&driver.nr)
    .bind(driver.lap)
    .bind(driver.gap)
    .bind(driver.leader_gap)
    .bind(driver.laptime)
    .bind(driver.sector_1)
    .bind(driver.sector_2)
    .bind(driver.sector_3)
    .execute(pool)
    .await?;
    Ok(())
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Laptime {
    pub time: DateTime<Utc>,
    pub lap: Option<i32>,
    pub laptime: i64
}

pub async fn get_laptimes(pool: &PgPool, nr: &str) -> Result<Vec<Laptime>> {
    let rows = sqlx::query(
        r#"select lap, min(laptime) as laptime, min(time) as time 
           from timing_driver 
           where nr = $1 and laptime != 0 
           group by lap order by lap"#
    )
    .bind(nr)
    .fetch_all(pool)
    .await?;

    let laptimes = rows.into_iter().map(|row| Laptime {
        time: row.get("time"),
        lap: row.get("lap"),
        laptime: row.get("laptime"),
    }).collect();

    Ok(laptimes)
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Gap {
    pub time: DateTime<Utc>,
    pub gap: i64
}

pub async fn get_gaps(pool: &PgPool, nr: &str) -> Result<Vec<Gap>> {
    let rows = sqlx::query(
        r#"select gap, time from timing_driver where nr = $1 and gap != 0"#
    )
    .bind(nr)
    .fetch_all(pool)
    .await?;

    let gaps = rows.into_iter().map(|row| Gap {
        time: row.get("time"),
        gap: row.get("gap"),
    }).collect();

    Ok(gaps)
}
