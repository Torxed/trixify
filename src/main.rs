use anyhow::Context;
use matrix_sdk::{
    authentication::{matrix::MatrixSession, AuthSession, SessionTokens},
    config::SyncSettings,
    ruma::{
        events::room::message::{MessageType, RoomMessageEventContent, SyncRoomMessageEvent},
        OwnedDeviceId, RoomId, UserId,
    },
    Client, Room, SessionMeta,
};
use serde::Deserialize;
use std::{collections::HashMap, convert::TryInto, fs, sync::Arc, time::Duration};
use tokio::{self, process::Command, time};
use tracing_subscriber::filter::LevelFilter;
use tracing_subscriber;
use url::Url;

/// Asynchronously checks the latest version of a repository using the nvrs library.
/// Asynchronously checks the latest version of a repository using the `nvrs` Rust library.
async fn check_version(source: &str, repo: &str) -> anyhow::Result<String> {
    // Use the Python nvchecker library via a python -c call
    // Ensure nvchecker is installed in the Python environment
    let py_code = format!(r#"
import asyncio
import structlog
import logging
from nvchecker import core
from nvchecker import __main__ as main
from nvchecker.util import Entries, ResultData, RawResult, RichResult

logger = structlog.get_logger(logger_name=__name__)
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR))

async def check_versions(entries):
    # oldvers :ResultData = {{'git': RichResult(version='v0.3.4', gitref='refs/tags/v0.3.4', revision='b00b1c09e05a35b6019eb98d7c8bc62cc0cb6424', url=None)}}
    oldvers :ResultData = {{}}


    max_concurrency = 10
    result_q: asyncio.Queue[RawResult] = asyncio.Queue()

    entry_waiter = core.EntryWaiter()
    task_sem = asyncio.Semaphore(max_concurrency)
    keymanager = core.KeyManager(None)
    dispatcher = core.setup_httpclient()
    futures = dispatcher.dispatch(
        entries, task_sem, result_q,
        keymanager, entry_waiter, 1, {{}},
    )

    result_coro = core.process_result(oldvers, result_q, entry_waiter)
    runner_coro = core.run_tasks(futures)

    results, _has_failures = await main.run(result_coro, runner_coro)

    #if len(oldvers) != 0:
    for application in results:
        if results.get(application, None) != oldvers.get(application, None):
            print(results[application].version)

asyncio.run(check_versions(
    {{
        "{source}": {{
            "source" : "{source}",
            "git" : "{repo}"
        }}
    }}
))
"#, );
    // Spawn Python to run nvchecker
    let output = Command::new("python3")
        .arg("-c")
        .arg(py_code)
        .output()
        .await
        .context("Failed to spawn python nvchecker call")?;
    let stdout = String::from_utf8(output.stdout)?;
    if stdout.trim().is_empty() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("Python nvchecker returned no output: {}", stderr.trim());
    }
    Ok(stdout.trim().to_string())
}

#[derive(Deserialize)]
struct General {
    homeserver: String,
    room:       String,
}

#[derive(Deserialize)]
struct Credentials {
    username:   String,
    token:      String,
    devicename: String,
}

#[derive(Deserialize, Clone)]
struct WatchingEntry {
    source: String,
    git:    String,
    users:  Vec<String>,
}

#[derive(Deserialize)]
struct Config {
    general:     General,
    credentials: Credentials,
    #[serde(rename = "watching")]
    watching:    HashMap<String, WatchingEntry>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing subscriber to suppress crypto key spam
    tracing_subscriber::fmt()
        .with_max_level(LevelFilter::ERROR)
        .init();

    // Load and parse configuration
    let toml_str = fs::read_to_string("trixify.toml").context("Failed to read trixify.toml")?;
    let cfg: Config = toml::from_str(&toml_str).context("Invalid TOML in trixify.toml")?;

    // Matrix client setup
    let homeserver = Url::parse(&cfg.general.homeserver).context("Invalid homeserver URL")?;
    let user_id = UserId::parse(&cfg.credentials.username).context("Invalid user ID")?;
    let room_id = RoomId::parse(&cfg.general.room).context("Invalid room ID")?;
    let device_id: OwnedDeviceId = cfg.credentials.devicename.clone()
        .try_into().context("Invalid device ID")?;

    let client = Client::builder()
        .homeserver_url(homeserver)
        .build()
        .await?;

    // Restore session
    let session = AuthSession::Matrix(MatrixSession {
        tokens: SessionTokens {
            access_token: cfg.credentials.token.clone(),
            refresh_token: None,
        },
        meta: SessionMeta { user_id: user_id.clone(), device_id },
    });
    client.restore_session(session).await?;

    // Shared client for background task
    let client_arc = Arc::new(client.clone());
    let watch_entries = cfg.watching.clone();
    let notify_room_id = room_id.clone();
    // Spawn a background task to check versions every hour and notify users in the configured room
    tokio::spawn({
        let client_arc = client_arc.clone();
        let watch_entries = watch_entries.clone();
        let notify_room_id = notify_room_id.clone();
        async move {
            let mut interval = time::interval(Duration::from_secs(3600));
            loop {
                interval.tick().await;
                for (key, entry) in &watch_entries {
                    match check_version(&entry.source, &entry.git).await {
                        Ok(version) => {
                            if let Some(room) = client_arc.get_room(&notify_room_id) {
                                for user_str in &entry.users {
                                    // Format a notification mentioning the user
                                    let msg = format!("{}: New version for '{}': {}", user_str, key, version);
                                    let content = RoomMessageEventContent::text_plain(msg);
                                    let _ = room.send(content).await;
                                }
                            }
                        }
                        Err(e) => eprintln!("Error checking version for '{}': {}", key, e),
                    }
                }
            }
        }
    });

    // Event handler: respond to !ping
    client_arc.add_room_event_handler(&notify_room_id.clone(), move |ev: SyncRoomMessageEvent, room: Room| async move {
        if let SyncRoomMessageEvent::Original(event) = ev {
            if room.room_id() != &notify_room_id {
                return;
            }
            if let MessageType::Text(text) = &event.content.msgtype {
                if text.body.trim() == "!ping" {
                    let reply = RoomMessageEventContent::text_plain("pong");
                    let _ = room.send(reply).await;
                }
            }
        }
    });

    // Sync loop
    client_arc.sync(SyncSettings::default()).await?;
    Ok(())
}
