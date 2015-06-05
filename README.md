# plugin.video.koddit

Reddit add-on for Kodi (ex XBMC)

Features :
* watch youtube or vimeo videos from subreddits
* add multireddits (multiple subreddits names separated by a "+") for a merged feed (eg "music+listentothis+psytrance")

Known issues :
* the addon sometimes yield an error that have no impact as far as i'm aware (working on it)
* sometimes very few or no results are returned (try adding subs containing a decent amount of videos such as /r/Documentaries or /r/listentothis)

TODO:
* fix the pagination issue
* add ability to log-in ?

# Manual installation

Download the plugin [here](https://github.com/known-as-bmf/plugin.video.koddit/archive/master.zip)

Then follow the steps bellow depending on your system and software version

##1. Open the addons folder

### Windows

* For Kodi : Press `Windows + R` and type in `%APPDATA%\kodi\addons`
* For XBMC : Press `Windows + R` and type in `%APPDATA%\XBMC\addons`

### Linux

* For Kodi : Open the `~/.kodi/addons` folder
* For XBMC : Open the `~/.xbmc/addons` folder

### OSX

* For Kodi : Open the `/Users/<your_user_name>/Library/Application Support/Kodi/addons` folder
* For XBMC : Open the `/Users/<your_user_name>/Library/Application Support/XBMC/addons` folder

##2. Install the add-on

* Extract the content of the zip in the `addons` folder
* Rename the extracted directory from `plugin.video.koddit-master` to `plugin.video.koddit`
* Done ! The plugin should show up in your video add-ons section.

# Troubleshooting

If you are having issues with the add-on, you can open a issue ticket and join your log file. The log file will contain your system user name and sometimes passwords of services you use in the software, so you may want to sanitize it beforehand. Detailed procedure [here](http://kodi.wiki/view/Log_file/Easy).

You should also try installing the dependancies manually via Kodi / XBMC. The dependancies are :

* xbmcswift2 (script.module.xbmcswift2 version 2.4.0)
* requests (script.module.requests version 2.6.0)
* youtube (plugin.video.youtube version 5.1.5)
* vimeo (plugin.video.vimeo version 4.1.2)

xbmcswift2 and requests should be in the "addon libraries" section of the official repository.
youtube and vimeo should be in the "video addons" sections of the official repository.
