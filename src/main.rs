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
use std::{fs};
use tokio;
use tracing_subscriber;
use url::Url;

#[derive(Deserialize)]
struct General {
    homeserver: String,
    room: String,
}

#[derive(Deserialize)]
struct Credentials {
    username: String,
    token: String,
    devicename: String,
}

#[derive(Deserialize)]
struct Config {
    general: General,
    credentials: Credentials,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    let toml_str = fs::read_to_string("trixify.toml").context("Failed to read trixify.toml")?;
    let cfg: Config = toml::from_str(&toml_str).context("Invalid TOML in trixify.toml")?;

    let homeserver = Url::parse(&cfg.general.homeserver).context("Invalid homeserver URL")?;
    let user_id = UserId::parse(&cfg.credentials.username).context("Invalid user ID")?;
    let room_id = RoomId::parse(&cfg.general.room).context("Invalid room ID")?;
    let device_id: OwnedDeviceId = cfg.credentials.devicename.clone()
        .try_into()
        .context("Invalid device ID")?;

    let client = Client::builder()
        .homeserver_url(homeserver)
        .build()
        .await?;

    // Restore session using access token
    let session = AuthSession::Matrix(MatrixSession {
        tokens: SessionTokens {
            access_token: cfg.credentials.token.clone(),
            refresh_token: None,
        },
        meta: SessionMeta {
            user_id: user_id.clone(),
            device_id: device_id.clone(),
        },
    });
    client.restore_session(session).await?;

    // Encryption keys (device + one-time) are uploaded automatically on restore_session

    client.add_room_event_handler(&room_id.clone(), move |ev: SyncRoomMessageEvent, room: Room| async move {
        if let SyncRoomMessageEvent::Original(event) = ev {
            if room.room_id() != &room_id {
                return;
            }
            if let MessageType::Text(text) = &event.content.msgtype {
                if text.body.trim() == "!ping" {
                    let reply = RoomMessageEventContent::text_plain("pong");
                    if let Err(e) = room.send(reply).await {
                        eprintln!("Error sending pong: {}", e);
                    }
                }
            }
        }
    });

    // Start syncing; this will keep running until an error occurs
    client.sync(SyncSettings::default()).await?;
    Ok(())
}
