# fooyin Rich Presence

This Python script allows you to display the current song, artist and album of the track you're listening on fooyin to Discord.

# Requirements

- fooyin (duh!)
- `pypresence`
- `pydbus`

Run `pip install -r requirements.txt` to install the required modules.

# What's next?

Run the script and play something via fooyin, it should display your current track and artist / album.

You may also run it as a service by moving the `fooyinrpc.service` file provided to `~/.config/systemd/user`, edit the /path/to/fooyinrpc.py to the one where the script is saved and run the following commands:

`systemctl --user daemon-reload`
`systemctl --user enable fooyin-rpc.service`
`systemctl --user start fooyin-rpc.service`
`systemctl --user status fooyin-rpc.service`

This way you can forget about it and always have Rich Presence for fooyin running.

# Last but not least, this was vibecoded, I'm too dumb for stuff like this 🫡
