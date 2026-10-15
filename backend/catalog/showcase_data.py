"""
The demo shops and products for the live showcase (`manage.py seed_showcase`), the same ones as in the README
screenshots. Every name is made up; owners get @example.test emails and no phone. Photos are in catalog/showcase/
(free Unsplash photos, credits in catalog/showcase/CREDITS.md).

Rasmitha's decision (15 Oct 2026): the live site may show these demo shops so visitors see a full marketplace. Only
shops and products are created: no orders, no reviews (made-up reviews would mislead), and each shop says it's a demo.
"""

DEMO_NOTE = "Demo shop with sample products."

# (owner key, owner name, shop slug, shop name, kind, category slug, area, delivery fee paise, delivery days, bio,
#  [(product name, description, price paise, stock, photo file stem)])
# fmt: off
SHOPS = [
    ("baker", "Lakshmi", "lakshmis-kitchen", "Lakshmi's Kitchen", "home_baker", "cakes", "Indiranagar", 4000, 1,
     "Small-batch cakes and cookies baked to order in a home kitchen.",
     [("Red velvet cupcakes, set of 6", "Soft red velvet sponge with cream cheese frosting.", 42000, 8,
       "red-velvet-cupcakes"),
      # The one product that is sold out on purpose, so visitors see the "Sold out" state.
      ("Banana walnut loaf", "A soft loaf with toasted walnuts. Keeps for three days.", 38000, 0, "banana-walnut-loaf"),
      ("Butter cookies, box of 12", "Crisp, buttery star cookies, packed in a gift box.", 32000, 12, "butter-cookies"),
      ("Chocolate truffle cake (1 kg)",
       "Rich chocolate sponge layered with truffle cream. Made fresh the day you order.", 85000, 8,
       "chocolate-truffle-cake")]),
    ("pickles", "Saroja", "ammas-pickles", "Amma's Pickles", "home_cook", "pickles", "Jayanagar", 3000, 2,
     "Family pickle recipes, sun-cured and packed in glass jars.",
     [("Mango pickle (500 g)", "Raw mango in sesame oil with mustard and chilli.", 24000, 12, "mango-pickle"),
      ("Lemon pickle (250 g)", "Tangy, mildly spiced lemon pickle.", 15000, 10, "lemon-pickle"),
      ("Mixed vegetable pickle (250 g)", "Carrot, chilli and lime, lightly spiced.", 18000, 8,
       "mixed-vegetable-pickle")]),
    ("snacks", "Revathi", "crunch-corner", "Crunch Corner", "home_cook", "snacks", "Basavanagudi", 3000, 1,
     "Tea-time snacks fried fresh in small batches.",
     [("Banana chips (200 g)", "Thin, crisp banana chips with a pinch of salt.", 12000, 15, "banana-chips"),
      ("Homemade samosas, 6 pieces", "Flaky pastry with spiced potato and peas.", 18000, 10, "samosas")]),
    ("artist", "Meera", "meera-art-studio", "Meera Art Studio", "artist", "art", "Malleshwaram", 6000, 4,
     "Hand-painted canvases and watercolours, each one signed.",
     [("Abstract canvas painting (12 x 12 in)", "Bold acrylic colours on stretched canvas, ready to hang.", 180000, 3,
       "abstract-canvas"),
      ("Fox watercolour (A4)", "An original watercolour on textured paper, unframed.", 90000, 4, "fox-watercolour")]),
    ("tailor", "Farah", "threads-by-farah", "Threads by Farah", "tailor", "tailoring", "HSR Layout", 5000, 5,
     "Blouse stitching, alterations and kids' wear, made to your measurements.",
     [("Blouse stitching", "Send your fabric and measurements; ready in five days.", 65000, 10, "blouse-stitching"),
      ("Alterations and hemming", "Trousers, sleeves and hems taken in or let out.", 25000, 20, "alterations"),
      ("Kids' cotton outfit", "Soft cotton everyday wear, sizes 2 to 8 years.", 79000, 6, "kids-clothes")]),
    ("crafter", "Nisha", "knot-and-paper", "Knot & Paper", "crafter", "crafts", "Banashankari", 5000, 3,
     "Macramé, gift wrapping and small handmade gifts.",
     [("Macramé wall hanging", "Hand-knotted cotton cord on a wooden dowel, about 60 cm long.", 145000, 4,
       "macrame-wall-hanging"),
      ("Hand-wrapped gift box", "Tell the maker the occasion; it's wrapped and tied with a handwritten tag.", 35000,
       15, "gift-box")]),
    ("jeweller", "Divya", "bead-and-thread", "Bead & Thread", "jewellery_maker", "jewellery", "Rajajinagar", 4000, 3,
     "Colourful beaded jewellery, strung by hand.",
     [("Beaded drop earrings", "Light, colourful drop earrings. Pick your colours in the note.", 45000, 12,
       "beaded-earrings"),
      ("Long beaded necklace", "A long strand of mixed beads.", 75000, 6, "beaded-necklace")]),
    ("potter", "Kavya", "clay-and-kiln", "Clay & Kiln", "crafter", "decor", "Whitefield", 7000, 3,
     "Wheel-thrown pottery for everyday use.",
     [("Pair of ceramic planters", "Two small glazed planters with drainage holes.", 95000, 6, "ceramic-planters"),
      ("Set of 2 coffee mugs", "Speckled glaze, 300 ml each.", 110000, 8, "ceramic-mugs")]),
]
# fmt: on


def owner_email(key: str) -> str:
    return f"showcase-{key}@example.test"
