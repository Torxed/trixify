# trixify

Matrix notify bot, using nvchecker as a backend.

:warning: This project was meant to be a "learning rust"-project, and thus is heavily guided by LLMs!

# Usage

## Account setup

First, create a matrix user with user type `bot`, and obtain an access token for your **bot** account by logging in once:

```bash
curl -XPOST -d \
  '{"type": "m.login.password", "identifier": {"user": "bot", "type": "m.id.user"}, "password": "your-bot-password", "initial_device_display_name": "trixify"}' \
  "https://matrix.domain.example/_matrix/client/v3/login"
```

This creates all the credentials you will need:

 - username
 - token
 - devicename

Enter the above three credentials in [trixify.toml](trixify.toml.example):

```toml
[credentials]
username = "@bot:matrix.domain.example"
token = "syt_abcdefgh_ijklmnopqrstuvxyz123_456789"
devicename = "ABCDEFGHIJ"
```

## Room setup

Create a room with your normal matrix user where the bot will live, and invite your bot after you've logged in once.

Then configure

```toml
[general]
homeserver = "https://matrix.domain.example"
room = "!rAbCdEfGhIjKlMnOpQ:matrix.domain.example"
```

## Monitor software releases

After this, configure and add as many watch objects as you wish using nvchecker syntax:

```toml
[watching."archinstall"]
source = "git"
git = "https://github.com/archlinux/archinstall.git"
users = [
	"@anton:matrix.domain.example"
]
```

This will ping `@anton:matrix.domain.example` each time a new version of archinstall is released, in room `!rAbCdEfGhIjKlMnOpQ:matrix.domain.example`.

And the message will look something like this:

> @anton:matrix.domain.example: New version for 'archinstall': 3.0.4