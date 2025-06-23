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
async fn check_version(name: &str, source: &str, repo: &str) -> anyhow::Result<String> {
    // Use the Python nvchecker library via a python -c call
    // Ensure nvchecker is installed in the Python environment
    let py_code = format!(r#"
import asyncio
import structlog
import logging
import json
import os
import sys
from nvchecker import core
from nvchecker import __main__ as main
from nvchecker.util import Entries, ResultData, RawResult, RichResult

logger = structlog.get_logger(logger_name=__name__)
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR))

def load_oldvers():
    """Load previous version data from file"""
    versions_file = 'trixify_versions.json'
    if os.path.exists(versions_file):
        try:
            with open(versions_file, 'r') as f:
                data = json.load(f)
                oldvers = {{}}
                for key, value in data.items():
                    if isinstance(value, dict) and 'version' in value:
                        oldvers[key] = RichResult(
                            version=value['version'],
                            gitref=value.get('gitref'),
                            revision=value.get('revision'),
                            url=value.get('url')
                        )
                return oldvers
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return {{}}

def save_oldvers(results):
    """Save current version data to file"""
    versions_file = 'trixify_versions.json'
    if os.path.exists(versions_file):
        with open(versions_file, 'r') as f:
            data = json.load(f)
    else:
        data = {{}}
    for key, result in results.items():
        if hasattr(result, 'version'):
            data[key] = {{
                'version': result.version,
                'gitref': getattr(result, 'gitref', None),
                'revision': getattr(result, 'revision', None),
                'url': getattr(result, 'url', None)
            }}
    
    try:
        with open(versions_file, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save version data: {{e}}", file=sys.stderr)

async def check_versions(entries):
    oldvers :ResultData = load_oldvers()
    max_concurrency = 10
    result_q: asyncio.Queue[RawResult] = asyncio.Queue()

    fh.write(f"{{oldvers}}\n")

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
    results["{name}"] = results.pop('git')

    fh.write(f"Result: {{results}}\n")

    # Check for version changes and save new results
    new_versions_found = False
    for application in results:
        if results.get(application, None) != oldvers.get(application, None):
            print(results[application].version)
            new_versions_found = True

    fh.write(f"New version: {{new_versions_found}}\n")
    
    # Save current results as the new oldvers for next run
    if new_versions_found or not oldvers:
        save_oldvers(results)

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
    #[serde(default = "default_interval")]
    interval:   u64,
}

fn default_interval() -> u64 {
    3600
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
        let check_interval = cfg.general.interval;
        async move {
            let mut interval = time::interval(Duration::from_secs(check_interval));
            loop {
                interval.tick().await;
                for (key, entry) in &watch_entries {
                    println!("Checking for new version for '{}'", key);
                    match check_version(&key, &entry.source, &entry.git).await {
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
                        Err(e) => {
                            if !e.to_string().contains("Python nvchecker returned no output") {
                                eprintln!("Error checking version for '{}': {}", key, e);
                            }
                        }
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
