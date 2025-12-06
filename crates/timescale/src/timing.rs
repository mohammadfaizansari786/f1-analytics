use sqlx::{PgPool, Row};
use anyhow::Result;

#[derive(Debug, Clone)]
pub struct Laptime {
    pub lap: i32,
    pub laptime: i32,
    pub time: i32,
}

#[derive(Debug, Clone)]
pub struct Gap {
    pub gap: i32,
    pub time: i32,
}

pub async fn insert_driver_timing(pool: &PgPool, driver: &crate::app_timing::Driver) -> Result<()> {
    // FIX: Use sqlx::query instead of sqlx::query! to skip compile-time DB checks
    sqlx::query(
        r#"insert into timing_driver (nr, lap, gap, leader_gap, laptime, sector_1, sector_2, sector_3)
        values ($1, $2, $3, $4, $5, $6, $7, $8)"#
    )
    .bind(driver.nr)
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

pub async fn get_driver_laptimes(pool: &PgPool, nr: i32) -> Result<Vec<Laptime>> {
    // FIX: Use manual mapping (row.get) instead of macro mapping
    let laptimes = sqlx::query(
        r#"select lap, min(laptime) as laptime, min(time) as time 
           from timing_driver 
           where nr = $1 and laptime != 0 
           group by lap order by lap"#
    )
    .bind(nr)
    .map(|row: sqlx::postgres::PgRow| Laptime {
        time: row.get("time"),
        lap: row.get("lap"),
        laptime: row.get("laptime"),
    })
    .fetch_all(pool)
    .await?;

    Ok(laptimes)
}

pub async fn get_driver_gaps(pool: &PgPool, nr: i32) -> Result<Vec<Gap>> {
    let gaps = sqlx::query(
        r#"select gap, time from timing_driver where nr = $1 and gap != 0"#
    )
    .bind(nr)
    .map(|row: sqlx::postgres::PgRow| Gap {
        time: row.get("time"),
        gap: row.get("gap"),
    })
    .fetch_all(pool)
    .await?;

    Ok(gaps)
}
