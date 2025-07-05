import enum
from uu import Error
import scrython
import imageio.v3 as imageio
import replicate
import os
import numpy as np

# Directory used for caching upscaled images to avoid re-upscaling when we just want to re-format
CACHE_DIR = "imgcache"
# Directory used for storing formatted images (i.e. upscaled and copyright removed)
FORMATTED_DIR = "formatted"

# ! DO NOT TOUCH. Redacting the copyright ultimately depend on these numbers
# See PNG output size at https://scryfall.com/docs/api/images
SCRYFALL_BASE_SIZE = (745, 1040)

# We upscale SCRYFALL_BASE_SIZE by x2 which results in a 600dpi image at 2.5" x 3.5" (596dpi to be exact)
# If you want more DPI you might need to change this number to 4 (the upscaling model does not support x3)
UPSCALE_FACTOR = 2

# No need to touch
DEBUG = False


class CardFrame(enum.Enum):
    MODERN = 1

    @classmethod
    def from_card(cls, card):
        card_frame = card["frame"]
        if card_frame == "2015":
            return CardFrame.MODERN
        else:
            raise Error(f"Frame {card_frame} nor supported")


class CardType(enum.Enum):
    CREATURE = 1
    PLANESWALKER = 2
    OTHER = 3

    @classmethod
    def from_card(cls, card):
        if "power" and "toughness" in card:
            return CardType.CREATURE
        elif "loyalty" in card:
            return CardType.PLANESWALKER
        else:
            return CardType.OTHER


class RedactBoxType(enum.Enum):
    MODERN_COPYRIGHT_DEFAULT = (430, 700, 970, 1040)
    MODERN_COPYRIGHT_CREATURE = (430, 700, 990, 1040)
    MODERN_COPYRIGHT_CREATURE_EXTRA_UNIVERSES_BEYOND = (430, 575, 970, 1040)
    MODERN_COPYRIGHT_PLANESWALKER = (430, 700, 990, 1040)

    def redactBox(self) -> tuple:
        return tuple([i * UPSCALE_FACTOR for i in self.value])


def search_and_process_card(query):
    query = query.strip()

    # Always need to query Scryfall to get the card metadata
    if ":" or "=" in query:
        card = scrython.cards.Search(q=query).data()[0]
    else:
        card = scrython.cards.Named(fuzzy=query).scryfallJson

    if "card_faces" in card:
        for face_number, face_card in enumerate(card["card_faces"]):
            process_card(
                card=card,
                frame=CardFrame.from_card(card),
                type=CardType.from_card(face_card),
                image_uris=face_card["image_uris"],
                face_number=face_number,
            )
    else:
        process_card(
            card=card,
            frame=CardFrame.from_card(card),
            type=CardType.from_card(card),
            image_uris=card["image_uris"],
            face_number=None,
        )


def process_card(card, frame, type, image_uris, face_number=None):
    # Using / in image names does not play were well with Linux
    cardname = f"{card['name'].replace('//', '&')}#{card['set'].upper()}#{(card['collector_number'])}"
    if face_number is not None:
        cardname += f"#face{face_number + 1}"
    print(f"[[{cardname}]] Found card: {card['scryfall_uri']}")

    if DEBUG:
        debug_path = os.path.join(CACHE_DIR, cardname + "_scryfall_original" + ".png")
        imageio.imwrite(debug_path, imageio.imread(image_uris["png"]))

    formatted_path = os.path.join(FORMATTED_DIR, cardname + ".png")
    cached_path = os.path.join(CACHE_DIR, cardname + ".png")

    if os.path.exists(formatted_path):
        print(f"[[{cardname}]] Already formatted")
        return
    elif os.path.exists(cached_path):
        print(f"[[{cardname}]] Using cached upscaled image, reformatting...")
        im = imageio.imread(cached_path)
    else:
        # You can change this model and upscale_factor if you want, but then make sure that the upscaling
        # is an integer (x2, x3, x4) so the code for redacting the copyright keeps working
        print(f"[[{cardname}]] No cached image found, upscaling and reformatting...")
        input = {
            "image": image_uris["png"],
            "enhance_model": "CGI",
            "upscale_factor": f"{UPSCALE_FACTOR}x",
            "face_enhancement": False,
            "output_format": "png",
        }
        output = replicate.run("topazlabs/image-upscale", input=input)
        output_url = output.url
        im = imageio.imread(output_url)
        imageio.imwrite(cached_path, im.astype(np.uint8))
        print(f"[[{cardname}]] Upscaled image saved to cache")

    # Pick a "band" from the border of the card to use as the border colour
    bordercolour = np.median(
        im[(im.shape[0] - 32) :, 200 : (im.shape[1] - 200)], axis=(0, 1)
    )

    # Remove copyright line
    match frame:
        case CardFrame.MODERN:
            match type:
                case CardType.CREATURE:
                    box = RedactBoxType.MODERN_COPYRIGHT_CREATURE.redactBox()
                    # Universes Beyond cards have an extra copyright line which is shifted
                    # depending on the type of the card
                    box_ub = (
                        RedactBoxType.MODERN_COPYRIGHT_CREATURE_EXTRA_UNIVERSES_BEYOND.redactBox()
                    )
                case CardType.PLANESWALKER:
                    box = RedactBoxType.MODERN_COPYRIGHT_PLANESWALKER.redactBox()
                    box_ub = None
                case CardType.OTHER:
                    box = RedactBoxType.MODERN_COPYRIGHT_DEFAULT.redactBox()
                    box_ub = None

            leftPix, rightPix, topPix, bottomPix = box
            im[topPix:bottomPix, leftPix:rightPix, :] = bordercolour
            if box_ub:
                leftPix, rightPix, topPix, bottomPix = box_ub
                im[topPix:bottomPix, leftPix:rightPix, :] = bordercolour

    # Pad image
    pad = 36 * UPSCALE_FACTOR  # Pad image by 1/8th of inch on each edge
    bordertol = 32  # Overfill onto existing border by 90px to remove white corners
    im_padded = np.zeros([im.shape[0] + 2 * pad, im.shape[1] + 2 * pad, 3])

    for i in range(0, 3):
        im_padded[pad : im.shape[0] + pad, pad : im.shape[1] + pad, i] = im[:, :, i]

    # Overfill onto existing border to remove white corners
    # Left
    im_padded[0 : im_padded.shape[0], 0 : pad + bordertol, :] = bordercolour

    # Right
    im_padded[
        0 : im_padded.shape[0],
        im_padded.shape[1] - (pad + bordertol) : im_padded.shape[1],
        :,
    ] = bordercolour

    # Top
    im_padded[0 : pad + bordertol, 0 : im_padded.shape[1], :] = bordercolour

    # Bottom
    im_padded[
        im_padded.shape[0] - (pad + bordertol) : im_padded.shape[0],
        0 : im_padded.shape[1],
        :,
    ] = bordercolour

    # Write image to disk
    imageio.imwrite(formatted_path, im_padded.astype(np.uint8))
    print(f"[[{cardname}]] Formatted image saved to disk")


if __name__ == "__main__":
    if not os.path.exists(FORMATTED_DIR):
        os.makedirs(FORMATTED_DIR)
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    # Loop through each card in cards.txt and scan em all
    with open("cards.txt", "r") as fp:
        for cardname in fp:
            search_and_process_card(cardname)
