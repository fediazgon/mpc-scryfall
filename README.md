# mpc-scryfall

*Adapted from [woogerboy21/mpc-scryfall](https://github.com/woogerboy21/mpc-scryfall).*

Simple tool to retrieve Scryfall scans of MTG cards, upscale the image using [real-esrgan](https://replicate.com/nightmareai/real-esrgan), and remove the copyright and holographic stamp to get the image ready for MPC. 

For sample results, see the images in the [sample_outputs](./sample_outputs) folder.

![How to use GIF](repo_assets/usage.gif)

## Requirements

* Basic knowledge on how to run Python.
* An internet connection (it uses Scryfall and Replicate APIs).
* A Replicate account for upscaling the images. Creeating an account is free, but you need to pay around 1$ every 100 requests (you only have to do it once per image).

## Usage Guide

1) Install the python packages listed in `requirements.txt`.
1) List all the cards that you want to download in the `cards.txt` file at the root of the repository.
1) In a terminal run `export REPLICATE_API_TOKEN=<YOUR_API_TOKEN>`.     
1) Run `python scryfall_formatter.py`.


## FAQ

### How to Search for a Specific Version or Set of a Card

**Set-specific searches**: To search within a particular set, add `s:` after the card name followed by the set code.

* Example: `Arcane Signet s:FIC`.

**Version-specific searches**: To select a specific version, use both `s:` for the set followed by `cn:` for the version number after the card name.

* Example: `Yuriko, the Tiger's Shadow s:CMM cn:690`

### Why are output images from Replicate cached?

In case you want to modify the posprocessing logic without the need of calling Replicate's API on every script execution. For example, you might decide that you want to use a different way of removing the copyright and the holographic stamp.