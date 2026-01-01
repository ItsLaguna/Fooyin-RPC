# fooyin Rich Presence

This Python script allows you to display the current song, artist and album of the track you're listening on fooyin to Discord.
<p align="center"> <img width="404" height="162" alt="Screenshot_20260101_200433" src="https://github.com/user-attachments/assets/08f18d4a-1e52-4bf1-a120-79c6874b4cdb" /> </p>

# Requirements

- `pypresence`
- `pydbus`

Run `pip install -r requirements.txt` to install the required modules.

# What's next?

Run the script and play something via fooyin, it should display your current track and artist / album.

You may also run it as a service by moving the `fooyinrpc.service` file provided to `~/.config/systemd/user`, open it, edit the `/path/to/fooyinrpc.py` to the one where the script is saved, save the file and then run the following commands:
```
systemctl --user daemon-reload
systemctl --user enable fooyinrpc.service
systemctl --user start fooyin-pc.service
````
By running `systemctl --user status fooyinrpc.service` you can check that it's been properly initialized.
This way you can forget about it and always have Rich Presence for fooyin running in the background.

### Last but not least, this was vibecoded, I'm too dumb for stuff like this 🫡
