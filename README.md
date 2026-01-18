# fooyin Rich Presence

This Python script allows you to display the current song, artist, and album of the track you're listening to on [fooyin](https://github.com/fooyin/fooyin) to Discord.
<p align="center"> <img width="404" height="162" alt="Screenshot_20260101_200433" src="https://github.com/user-attachments/assets/08f18d4a-1e52-4bf1-a120-79c6874b4cdb" /> </p>

# Requirements

- [fooyin](https://github.com/fooyin/fooyin)
- `pypresence`
- `pydbus`

Run `pip install -r requirements.txt` to install the required modules.

# What's next?

Run the script and play something via fooyin, it should display your current track and artist / album.

You may also run it as a service by moving the `fooyinrpc.service` file provided to `~/.config/systemd/user`, edit the service file and replace `/path/to/fooyinrpc.py` to the one where the script is saved, save the file and then run the following commands:
```
systemctl --user daemon-reload
systemctl --user enable --now fooyinrpc.service
````
By running `systemctl --user status fooyinrpc.service` you can check that it's been properly initialized.
This way you can forget about it and always have Rich Presence for fooyin running in the background.

‎ 

# Fooyin Rich Presence (Album Art Ver.)
<p align="center"> <img width="402" height="165" alt="image" src="https://github.com/user-attachments/assets/0766ff90-e8c9-433b-bd28-94db3a8c05b0" /> </p>

There's another version of the script that'll be offered under Releases, which allows for the embedded album art of the track (if there's any) to be displayed in the Rich Presence (if someone ever cares and wants to add the option to use a cover already present in the folder where the audio file is, feel free to make Pull Request).

# Requirements (for this version)
- All of the other requirements
- Flask (`pip install flask`)
- A web server app
- A domain (if you want others to see them)
  
# What to do?

The steps are provided for the environment I used (Fedora and Caddy as the web server), feel free to contribute if you're in a different one and using a different web server app.

# Folder, Art and Permissions

Before doing the server bit, create the folder needed for the art and give permissions and label it so the album art can be displayed:
```
sudo mkdir -p /var/www/fooyinart
sudo chown <youruser>:www-data /var/www/fooyinart
sudo chmod -R 755 /var/www/fooyinart
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/fooyinart(/.*)?"
sudo restorecon -Rv /var/www/fooyinart
```
Keep in mind that these path used is the default one in the script for `USE_CUSTOM_PATH`.

If you set it to false, you'll have to specify the path where the script is located, as that's where the album art is generated.

# Caddy

Install Caddy and create a file called Caddyfile (`sudo nano /etc/caddy/Caddyfile`) and add the following to it:

```
<replace with your domain/subdomain/hostname> {
    handle /upload {
        reverse_proxy 127.0.0.1:7000
    }

    handle /_current_artwork {
        root * /var/www/fooyinart/
        header Content-Type image/jpeg
        file_server
    }

    handle {
        abort
    }
}
```
Then save (Ctrl + O, then Enter) and exit (Ctrl + X). 

Once this is done restart Caddy (`sudo systemctl restart caddy`) and the script just to make sure, then proceed to test it by accessing `https://yourdomain/_custom_Artwork` and verify that it's working.

If everything has gone correctly, you should be able to see the album art that's embedded on your file, sadly there's a slightly delay when changing songs but couldn't do much about it.

### Last but not least, this script was "vibecoded", I'm too dumb for stuff like this 🫡
