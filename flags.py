# ============================================================================
# Copyright © 2026 Valrik Thakur (@valriks)
#
# Created & Developed by: Valrik Thakur
# Brand / Network: VTH NETWORK (@vthchannel)
#
# This source code is proprietary content created by Valrik Thakur.
# Unauthorized removal, modification, replacement, or concealment of the
# original author/brand credits is strictly prohibited.
#
# Redistribution, resale, rebranding, or claiming this work as your own
# without explicit permission from the author is prohibited.
#
# Any authorized use or modification must retain this copyright notice
# and the original author/brand credits.
#
# Created by Valrik Thakur | @valriks
# Powered by VTH NETWORK | @vthchannel
# ============================================================================


"""Country name -> flag emoji (same table the main bot uses for Server 3 / Server 2)."""
import re

_A2 = {'aruba': 'AW', 'afghanistan': 'AF', 'angola': 'AO', 'albania': 'AL', 'andorra': 'AD', 'uae': 'AE', 'argentina': 'AR', 'armenia': 'AM', 'antigua  barbuda': 'AG', 'australia': 'AU', 'austria': 'AT', 'azerbaijan': 'AZ', 'burundi': 'BI', 'belgium': 'BE', 'benin': 'BJ', 'burkina faso': 'BF', 'bangladesh': 'BD', 'bulgaria': 'BG', 'bahrain': 'BH', 'bahamas': 'BS', 'bosnia': 'BA', 'belarus': 'BY', 'belize': 'BZ', 'bolivia': 'BO', 'brazil': 'BR', 'barbados': 'BB', 'brunei': 'BN', 'bhutan': 'BT', 'botswana': 'BW', 'central african rep': 'CF', 'canada': 'CA', 'switzerland': 'CH', 'chile': 'CL', 'ivory coast': 'CI', 'cameroon': 'CM', 'dr congo': 'CD', 'congo': 'CG', 'colombia': 'CO', 'comoros': 'KM', 'cape verde': 'CV', 'costa rica': 'CR', 'cuba': 'CU', 'cyprus': 'CY', 'czech republic': 'CZ', 'germany': 'DE', 'djibouti': 'DJ', 'dominica': 'DM', 'denmark': 'DK', 'dominican rep': 'DO', 'algeria': 'DZ', 'ecuador': 'EC', 'egypt': 'EG', 'eritrea': 'ER', 'spain': 'ES', 'estonia': 'EE', 'ethiopia': 'ET', 'finland': 'FI', 'fiji': 'FJ', 'france': 'FR', 'micronesia': 'FM', 'gabon': 'GA', 'united kingdom': 'GB', 'georgia': 'GE', 'ghana': 'GH', 'gibraltar': 'GI', 'guinea': 'GN', 'guadeloupe': 'GP', 'gambia': 'GM', 'guineabissau': 'GW', 'equatorial guinea': 'GQ', 'greece': 'GR', 'grenada': 'GD', 'guatemala': 'GT', 'french guiana': 'GF', 'guam': 'GU', 'guyana': 'GY', 'hong kong': 'HK', 'honduras': 'HN', 'croatia': 'HR', 'haiti': 'HT', 'hungary': 'HU', 'indonesia': 'ID', 'isle of man': 'IM', 'india': 'IN', 'ireland': 'IE', 'iran': 'IR', 'iraq': 'IQ', 'iceland': 'IS', 'israel': 'IL', 'italy': 'IT', 'jamaica': 'JM', 'jordan': 'JO', 'japan': 'JP', 'kazakhstan': 'KZ', 'kenya': 'KE', 'kyrgyzstan': 'KG', 'cambodia': 'KH', 'kiribati': 'KI', 'saint kitts': 'KN', 'south korea': 'KR', 'kuwait': 'KW', 'laos': 'LA', 'lebanon': 'LB', 'liberia': 'LR', 'libya': 'LY', 'saint lucia': 'LC', 'liechtenstein': 'LI', 'sri lanka': 'LK', 'lesotho': 'LS', 'lithuania': 'LT', 'luxembourg': 'LU', 'latvia': 'LV', 'macau': 'MO', 'morocco': 'MA', 'monaco': 'MC', 'moldova': 'MD', 'madagascar': 'MG', 'maldives': 'MV', 'mexico': 'MX', 'marshall islands': 'MH', 'north macedonia': 'MK', 'mali': 'ML', 'malta': 'MT', 'myanmar': 'MM', 'montenegro': 'ME', 'mongolia': 'MN', 'n mariana isl': 'MP', 'mozambique': 'MZ', 'mauritania': 'MR', 'martinique': 'MQ', 'mauritius': 'MU', 'malawi': 'MW', 'malaysia': 'MY', 'namibia': 'NA', 'niger': 'NE', 'nigeria': 'NG', 'nicaragua': 'NI', 'netherlands': 'NL', 'norway': 'NO', 'nepal': 'NP', 'nauru': 'NR', 'new zealand': 'NZ', 'oman': 'OM', 'pakistan': 'PK', 'panama': 'PA', 'peru': 'PE', 'philippines': 'PH', 'palau': 'PW', 'papua new guinea': 'PG', 'poland': 'PL', 'puerto rico': 'PR', 'north korea': 'KP', 'portugal': 'PT', 'paraguay': 'PY', 'palestine': 'PS', 'qatar': 'QA', 'reunion': 'RE', 'romania': 'RO', 'russia': 'RU', 'rwanda': 'RW', 'saudi arabia': 'SA', 'sudan': 'SD', 'senegal': 'SN', 'singapore': 'SG', 'solomon islands': 'SB', 'sierra leone': 'SL', 'el salvador': 'SV', 'san marino': 'SM', 'somalia': 'SO', 'serbia': 'RS', 'south sudan': 'SS', 'sao tome': 'ST', 'suriname': 'SR', 'slovakia': 'SK', 'slovenia': 'SI', 'sweden': 'SE', 'eswatini': 'SZ', 'seychelles': 'SC', 'syria': 'SY', 'chad': 'TD', 'togo': 'TG', 'thailand': 'TH', 'tajikistan': 'TJ', 'turkmenistan': 'TM', 'timorleste': 'TL', 'tonga': 'TO', 'trinidad  tobago': 'TT', 'tunisia': 'TN', 'turkey': 'TR', 'tuvalu': 'TV', 'taiwan': 'TW', 'tanzania': 'TZ', 'uganda': 'UG', 'ukraine': 'UA', 'uruguay': 'UY', 'usa': 'US', 'uzbekistan': 'UZ', 'vatican city': 'VA', 'st vincent  grenadines': 'VC', 'venezuela': 'VE', 'vietnam': 'VN', 'vanuatu': 'VU', 'samoa': 'WS', 'kosovo': 'XK', 'yemen': 'YE', 'south africa': 'ZA', 'zambia': 'ZM', 'zimbabwe': 'ZW', 'united states': 'US', 'united states virtual': 'US', 'uk': 'GB', 'england': 'GB', 'korea': 'KR', 'cote divoire': 'CI', 'united arab emirates': 'AE', 'czechia': 'CZ', 'burma': 'MM', 'east timor': 'TL', 'macedonia': 'MK'}

def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", str(s or "").lower()).strip()

def _emoji(a2):
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in a2.upper())

def flag_for(name):
    n = _norm(name)
    a2 = _A2.get(n) or _A2.get(n.replace(" virtual", ""))
    return _emoji(a2) if a2 else "\U0001F30D"

_FLAG_RX = re.compile("[\U0001F1E6-\U0001F1FF]{2}")

def strip_flags(text):
    return _FLAG_RX.sub("", str(text or "")).strip()
