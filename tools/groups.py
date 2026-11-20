# Astra Novum 2240 ethnic groups.
# Each group: (key, name, family, homeland/2240 note, seeds)
# seed = (lat, lon, weight, radius_deg). Homeland seeds use weight ~1-3; 2240
# migration seeds (marked by the note) use lower weights so they show as
# minorities or mixed zones unless they dominate a thinly peopled area.

EARTH = [
 # ---- Slavic
 ("russian","Russians","Slavic","European Russia; large share of the 2240 Siberian boom",
  [(55.7,37.6,3,9),(59.9,30.3,2,3),(53,45,2,5),(57,50,1.5,7),(56.8,60.6,2,6),(55,73,1.5,6),(55,83,1.8,7),(56,92,1.3,6),(52.3,104,1.2,6),(48.5,135,1.2,6),(43.1,131.9,1,4),(62,129.7,0.7,5),(60,75,0.9,7),(47.2,39.7,1.5,5)]),
 ("ukrainian","Ukrainians","Slavic","Ukraine",[(50.4,30.5,2.5,6),(49.8,24,2,4),(48.5,35,1.8,5),(46.5,32,1.3,4)]),
 ("belarusian","Belarusians","Slavic","Belarus",[(53.9,27.6,2.5,4)]),
 ("polish","Poles","Slavic","Poland",[(52.2,21,2.5,5),(51,17,2,4),(50,20,2,3),(53.5,18,1.5,3)]),
 ("czech","Czechs","Slavic","Bohemia, Moravia",[(50,15,2,3),(49.3,17,1.4,1.5)]),
 ("serbcroat","South Slavs (Serbo-Croatian)","Slavic","Western Balkans",[(44.8,20.5,2,3),(45.5,16,1.8,3),(43.9,18,1.6,2.5),(46,14.5,1.2,1.5)]),
 ("bulgarian","Bulgarians and Macedonians","Slavic","Eastern Balkans",[(42.7,25,2,3),(41.6,21.7,1.3,1.5)]),
 # ---- Germanic / Celtic / Baltic / Finnic
 ("german","Germans","Germanic","Germany, Austria, Swiss plateau",[(51,10,3,5),(48,11.5,2,3),(53.5,10,2,3),(48.2,16,1.5,2),(47.2,8,1.2,1.5)]),
 ("dutch","Dutch and Flemish","Germanic","Low Countries, inland of the 2240 coast",[(52,5.5,2.9,2.2),(51,4.4,2.2,1.5)]),
 ("english","English","Germanic","England",[(52.5,-1.5,2.6,3),(51.5,-0.1,1.5,1.5)]),
 ("scots","Scots","Celtic","Scotland",[(56.5,-4,2,2.5)]),
 ("irish","Irish","Celtic","Ireland",[(53.2,-8,2.4,2.5)]),
 ("scandinavian","Scandinavians","Germanic","Sweden, Norway, Denmark; settlers in ice-free Greenland",[(59.5,15,2,4),(61,9,1.8,4),(64,18,1,5),(56,10,1.6,2),(66,-45,1.2,6),(62,-48,1.3,4),(72,-42,0.8,6),(78.2,15.6,1.2,3)]),
 ("finnic","Finns and Karelians","Finnic","Finland, Karelia",[(62,25.5,2,4),(63,33,0.7,3)]),
 # ---- Romance / Greek / others in Europe
 ("french","French","Romance","France, Wallonia, Romandy",[(47,2.5,3,5),(45,5,2,3),(44,1,1.6,3),(48.5,-2,1.5,2),(50.5,4.8,1,1)]),
 ("spanish","Spaniards","Romance","Castile, Andalusia",[(40.4,-3.7,2.5,4),(37.5,-5,2,3),(42.5,-6,1.5,2.5),(28.3,-16,1.6,2)]),
 ("catalan","Catalans","Romance","Catalonia, Valencia, Balearics",[(41.8,1.8,2,1.8),(39.5,-0.5,1.3,1.5)]),
 ("portuguese","Portuguese","Romance","Portugal",[(39.5,-8.2,2.5,2.5),(38.5,-28,1.2,2),(32.7,-17,1.2,1.2)]),
 ("italian","Italians","Romance","Italy",[(45,9.5,2.5,2.5),(43,12.3,2.5,2.5),(40.8,15.5,2.2,2.5),(37.5,14,1.8,1.5),(40,9,1.3,1)]),
 ("romanian","Romanians and Moldovans","Romance","Danube and Carpathians",[(45.5,25,2.5,3.5),(47,28.5,1.6,1.5)]),
 ("hungarian","Hungarians","Ugric","Pannonian basin",[(47.2,19.3,2.5,2.6)]),
 ("greek","Greeks","Hellenic","Greece, Cyprus",[(38.5,22.5,2.5,3),(40.6,23,2,2),(35.3,25,1.6,1.5),(37.5,26,1.2,2),(35,33.2,1.6,1)]),
 ("albanian","Albanians","Albanian","Albania, Kosovo",[(41.2,20,2,1.5),(42.6,21,1.3,1)]),
 # ---- Caucasus, Turkic west, Iranian
 ("georgian","Georgians","Kartvelian","Georgia",[(42,43.5,2.8,2.2)]),
 ("armenian","Armenians","Armenian","Armenia",[(40.2,44.7,2.8,1.8)]),
 ("ncaucasian","Other North Caucasians","Caucasian","Chechnya, Dagestan and the northern slope",[(43,46,2,2.2),(43.5,43,1.3,1.5)]),
 ("azerbaijani","Azerbaijanis","Turkic","Azerbaijan, Iranian Azerbaijan",[(40.4,48,2,2.5),(38,46.5,2,2.5)]),
 ("turkish","Turks","Turkic","Anatolia, Thrace",[(39.5,32.8,3,5),(41,29,2,2.5),(38.4,27.2,1.5,2),(37,35.3,1.5,2.5)]),
 ("kurdish","Kurds","Iranian","Kurdistan",[(37.5,42,2.4,3),(36.2,44,1.6,2),(35.3,47,1.2,2)]),
 ("persian","Persians","Iranian","Iranian plateau",[(35.7,51.4,3,5),(32.6,51.7,2,4),(29.6,52.5,2,3),(36.3,59.6,1.5,3)]),
 ("baloch","Baloch","Iranian","Balochistan",[(28,63,2,3.5)]),
 ("pashtun","Pashtuns","Iranian","Afghan south and east, Pakistani frontier",[(31.6,65.7,2,3),(34,71.5,2,2.5)]),
 ("tajik","Tajiks","Iranian","Tajikistan, northern Afghanistan",[(38.6,68.8,2,2.5),(36.5,69.5,1.5,2.5),(34.5,62,1,2)]),
 # ---- Semitic, Afroasiatic north
 ("levantine","Levantine Arabs","Semitic","Syria, Lebanon, Jordan, Palestine",[(33.5,36.3,2.5,3),(31.9,35.9,1.6,2)]),
 ("jewish","Israelis","Semitic","Israel",[(32,34.9,2.2,1.1)]),
 ("iraqi","Mesopotamian Arabs","Semitic","Tigris and Euphrates; much of the old delta under the sea",[(33.3,44.4,2.5,3.5),(31.5,46,1.5,2.5)]),
 ("gulf","Najdi and Hejazi Arabs","Semitic","Arabian interior and Hejaz; its coasts drowned or abandoned for heat",[(24.7,46.7,2.4,5),(21.5,39.8,1.8,3)]),
 ("egyptian","Egyptians","Semitic","Nile valley above the drowned delta",[(30,31.2,2.8,2.5),(26.5,31.7,2,2),(24,32.9,1.2,1.5)]),
 ("maghrebi","Maghrebi Arabs","Semitic","Maghreb coast; large communities in France, Spain and Italy",[(34,-5,2,3),(36.7,3,2,3),(36.8,10.2,2,2),(32.9,13.2,1.5,2.5),(48.8,2.4,0.55,3),(43.3,5.4,0.6,2),(40.4,-3.7,0.4,3),(45.5,9.2,0.35,2.5)]),
 ("amazigh","Amazigh (Berbers)","Berber","Atlas and Kabylie",[(31.5,-7.5,2.2,2.5),(36.5,4.3,1.3,1),(29.5,-9,1.2,1.5)]),
 ("tuareg","Tuareg","Berber","Central Sahara",[(19,7,1.6,4),(22,4,1.2,3.5)]),
 # ---- Central Asia & Siberia natives
 ("kazakh","Kazakhs","Turkic","Kazakh steppe; spreading north into a warmer western Siberia",[(48,68,2.5,7),(43.3,76.9,2,3),(51.2,71.4,2,4),(44,52,1.5,2.5),(54.5,70,0.6,4)]),
 ("uzbek","Uzbeks","Turkic","Uzbekistan, Fergana; migrant towns across southern Siberia",[(41.3,69.2,2.5,3),(40.5,72,2,2),(39.7,66.9,2,2.5),(55,73.4,0.45,4),(56,92.9,0.35,4),(57,65.5,0.35,4)]),
 ("turkmen","Turkmens","Turkic","Turkmenistan",[(38,58.4,2.6,4),(40,53.5,1.6,2.5)]),
 ("kyrgyz","Kyrgyz","Turkic","Tian Shan",[(42.9,74.6,2,2.5),(41,75,1.4,2)]),
 ("tatar","Volga Tatars","Turkic","Middle Volga",[(55.8,49.1,2.4,2.2)]),
 ("bashkir","Bashkirs","Turkic","Southern Urals",[(54.7,56,2,2.2)]),
 ("uyghur","Uyghurs","Turkic","Tarim basin",[(39.5,76,2.4,3.5),(43.8,87.6,1.3,2.5),(41.7,86,1.5,3)]),
 ("mongol","Mongols","Mongolic","Mongolia, Inner Mongolia",[(47.9,106.9,2.4,6),(47,96,1.5,6),(42,113,1.2,4)]),
 ("buryat","Buryats","Mongolic","Lake Baikal",[(52,108,1.8,3.5)]),
 ("sakha","Sakha (Yakuts)","Turkic","Lena basin",[(62,129.7,1.8,7),(65,120,1,7)]),
 ("ugric","Khanty, Mansi and Nenets","Uralic","Ob and Yamal; a minority since the gas and grain booms",[(64,70,0.8,8),(67,76,0.6,6)]),
 ("evenk","Evenks and Evens","Tungusic","Central Siberian Plateau",[(64,100,0.9,10),(64,140,0.6,8)]),
 ("sibiryak","Sibiryaks (new Siberians)","2240 hybrid","Born in the Siberian boom: Russian, Central Asian, Chinese and Korean roots mixed in the new Yenisei, Angara and Lena cities",
  [(58,93,1.5,6),(56.5,101.6,1.4,5),(60.5,113,1.2,6),(55.5,85,0.9,5),(61,76.5,0.9,5),(53.5,113,0.9,5),(66,88,0.8,6)]),
 # ---- South Asia
 ("hindustani","Hindustanis (Hindi-Urdu)","Indo-Aryan","Ganges plain, Rajasthan, Madhya Pradesh",[(26.8,80.9,3,5),(28.6,77.2,2.5,3),(25.6,85.1,2.4,3),(26.9,75.8,2,3.5),(23.3,77.4,2,4),(25.3,83,2,2.5)]),
 ("punjabi","Punjabis","Indo-Aryan","Punjab",[(31.5,74.3,2.5,2.5),(30.7,76.8,1.8,1.8),(33.6,73,2.6,1.5),(43.6,-79.7,0.3,1.5)]),
 ("sindhi","Sindhis","Indo-Aryan","Lower Indus above the new shore",[(26,68.5,2,2.5)]),
 ("bengali","Bengalis","Indo-Aryan","Bengal, pushed inland by the drowned delta into Assam, Bihar and Myanmar",[(23.8,90.4,2.5,2),(24.5,88.3,2.2,2),(25.5,91.5,1.5,1.8),(26.2,92.5,1.3,2),(25.5,87,0.8,2),(22,94,0.5,2)]),
 ("gujarati","Gujaratis","Indo-Aryan","Gujarat",[(23,72.6,2.4,2.5),(-6.8,39.3,0.2,2),(51.5,-0.1,0.2,1.5)]),
 ("marathi","Marathis","Indo-Aryan","Maharashtra",[(19.5,75,2.6,3),(18.5,73.9,1.8,1.5)]),
 ("odia","Odias","Indo-Aryan","Odisha",[(20.5,84.5,2.2,2.2)]),
 ("nepali","Nepalis","Indo-Aryan","Himalayan foothills",[(28,84,2,2.5)]),
 ("sinhalese","Sinhalese","Indo-Aryan","Sri Lanka",[(7.3,80.6,2,1.3)]),
 ("assamese","Assamese and Northeast peoples","Indo-Aryan/Tibeto-Burman","Brahmaputra valley and the north-eastern hills",[(26.5,93,2.2,2),(25,94,1.6,1.5),(23.5,92.8,1.3,1.2)]),
 ("kashmiri","Kashmiris","Indo-Aryan","Vale of Kashmir",[(34.1,74.8,2.2,1.4)]),
 ("tamil","Tamils","Dravidian","Tamil Nadu, northern Sri Lanka",[(11,78.5,2.6,2.5),(13.1,80.3,1.5,1),(9.4,80.2,1,0.8),(1.35,103.8,0.6,0.6)]),
 ("telugu","Telugus","Dravidian","Andhra and Telangana",[(16.5,79.5,2.6,2.8)]),
 ("kannada","Kannadigas","Dravidian","Karnataka",[(14.5,76,2.5,2.2)]),
 ("malayali","Malayalis","Dravidian","Kerala; a large presence in the inland Gulf",[(10,76.5,2.3,1.2),(24.7,46.7,0.3,4)]),
 ("gond","Adivasi peoples","Austroasiatic/Dravidian","Central Indian hills",[(22,82,1.3,2.5),(23.4,85.3,1.3,2)]),
 # ---- East Asia
 ("hannorth","Northern Han","Sinitic","North China plain, Manchuria; settlers across the Amur",[(36,115,3,6),(39.9,116.4,2,3),(34.5,109,2.2,4),(36,103.8,1.4,3),(45.8,126.6,2.2,4),(41.8,123.4,2,3),(30.6,104,1,3),(48.5,135,0.5,4),(52.3,104,0.4,4),(50.3,127.5,0.6,3),(43.8,87.6,1.2,2.5)]),
 ("hansw","Southwestern Han","Sinitic","Sichuan basin, Chongqing, Yunnan-Guizhou",[(30.6,104,2.8,3.5),(29.6,106.5,2.4,2.5),(25,102.7,1.6,2.5),(26.6,106.7,1.4,2)]),
 ("wu","Wu Chinese","Sinitic","Lower Yangtze above the drowned delta",[(30.5,119.5,2.6,2.2),(31.8,118.8,1.8,1.5)]),
 ("cantonese","Cantonese","Sinitic","Lingnan uplands; Hakka hills",[(23.5,113.5,2.4,2.2),(23,110,1.8,2.2),(1.35,103.8,0.4,0.8)]),
 ("min","Min Chinese","Sinitic","Fujian, Taiwan",[(26,117.5,2.4,2.2),(24,121,2,1.3),(24.5,115.5,1.2,1.2)]),
 ("hui","Hui","Sinitic","Ningxia, Gansu",[(37,106,1.6,2.5)]),
 ("tibetan","Tibetans","Tibeto-Burman","Tibetan plateau",[(30.5,91,2,3.5),(33,97,1.5,3.5),(33.5,85,1,4)]),
 ("zhuang","Zhuang","Tai","Guangxi",[(23.5,108,2.2,2.2)]),
 ("korean","Koreans","Koreanic","Korean peninsula; in the Russian Far East",[(37.5,127,2.6,2),(39,126,2,2),(35.5,128.5,1.8,1.5),(43.1,131.9,0.5,2.5),(48.5,135,0.3,3)]),
 ("japanese","Japanese","Japonic","Japanese islands, highland-shifted",[(36,138.5,3,3),(34.7,135.5,2,2),(43,142.5,1.8,2.5),(33,131,1.6,1.8),(21.3,-157.9,0.6,1.2)]),
 # ---- Southeast Asia
 ("vietnamese","Vietnamese (Kinh)","Austroasiatic","Vietnamese highlands and coast above the drowned deltas",[(21,105.8,2.2,2),(16.5,107.5,2,2),(12.5,108,1.6,2.5)]),
 ("thai","Thai","Tai","Chao Phraya highlands, Isan",[(16,101,2.4,3),(18.8,99,1.8,2),(14.5,101.5,1.5,1.5)]),
 ("lao","Lao","Tai","Mekong north",[(18.5,103.5,1.8,2.5)]),
 ("khmer","Khmer","Austroasiatic","Cambodia",[(12.5,104.5,2.2,2.2)]),
 ("burman","Bamar (Burmese)","Tibeto-Burman","Irrawaddy dry zone",[(21,95.8,2.5,3),(19,96.2,1.5,2)]),
 ("shan","Shan and hill peoples","Tai","Shan plateau, Kachin hills",[(21.5,98.5,1.6,2.5),(25.5,97.5,1.2,2)]),
 ("malay","Malays","Austronesian","Malaya, Sumatra coasts, Borneo",[(3.5,102,2.2,2.5),(0.5,101.5,1.8,2.5),(1.5,111,1.2,3)]),
 ("javanese","Javanese","Austronesian","Central and East Java",[(-7.5,110.5,3,2.2),(-7.8,112.5,2.4,1.5),(-4,104,0.6,2)]),
 ("sundanese","Sundanese","Austronesian","West Java",[(-6.9,107.6,2.4,1.2)]),
 ("sulawesi","Bugis and Sulawesi peoples","Austronesian","Celebes",[(-3,120,1.8,3)]),
 ("filipino","Tagalog and Luzon peoples","Austronesian","Luzon",[(15.5,121,2.4,2.2),(21.3,-157.9,0.5,1.2)]),
 ("visayan","Visayans","Austronesian","Visayas, Mindanao",[(10.5,123.5,2.2,2),(7.5,125,1.8,2)]),
 ("timorese","Timorese, Florenese and Moluccans","Austronesian","Lesser Sundas, Timor, Moluccas",[(-3.5,128.5,1.8,3),(-9,125,1.8,2),(-8.6,121,1.5,2.5),(-8.6,117,1.2,1.5)]),
 ("papuan","Papuans","Papuan","New Guinea",[(-5.5,143,1.8,5),(-4,138,1.3,4)]),
 # ---- Oceania
 ("anglo_au","Anglo-Australians","Germanic","Australian south-east and south-west, Aotearoa",[(-34,150.8,2.4,3),(-37.8,145,2.2,2.5),(-27.5,153,1.6,2.5),(-32,116,1.5,2.5),(-35,138.6,1.4,2),(-41,174,1.3,2.5)]),
 ("aboriginal","Aboriginal Australians","Pama-Nyungan","Australian interior and north",[(-22,133,0.9,10),(-15,130,0.9,4.5),(-18,140,0.6,5)]),
 ("maori","Maori","Polynesian","Aotearoa North Island",[(-38.5,176,1.2,2)]),
 ("polynesian","Pacific Islanders","Austronesian","Polynesia, Melanesia, Micronesia",[(20.8,-156.8,1.6,2.5),(-17.5,178,1.5,4),(-14,-172,1.4,4),(-17.5,-149.5,1.2,4),(-9.5,160,1.4,4),(-21,165,1,3),(7,158,0.8,5)]),
 # ---- Africa
 ("hausa","Hausa","Chadic","Northern Nigeria, Niger",[(12,8.5,2.8,3.5),(13.5,7,1.6,3)]),
 ("fulani","Fula","Atlantic","Sahel from Senegal to Cameroon",[(14,-14,1.4,5),(11.5,-11,1.5,3),(10.5,12,1.3,3),(14.5,-1,1,4),(12.5,1.5,0.9,4)]),
 ("kanuri","Kanuri and Chadians","Saharan","Lake Chad, Chad",[(12.5,14,1.6,3),(12.1,15,1.3,3),(9.5,18,1.4,3)]),
 ("yoruba","Yoruba","Volta-Niger","South-west Nigeria, Benin",[(7.6,4,2.8,2.5)]),
 ("igbo","Igbo","Volta-Niger","South-east Nigeria",[(6,7.5,2.6,1.8)]),
 ("niger_delta","Niger Delta and Middle Belt peoples","Benue-Congo","Middle Belt, delta uplands",[(9,8.5,1.8,3),(6.5,6,1.2,1.3)]),
 ("akan","Akan","Kwa","Ghana, Ivory Coast, Togo",[(6.8,-1.5,2.5,2.5),(7,-5,1.8,2.5),(7,1,1.2,1.2)]),
 ("mande","Mande peoples","Mande","Mali, Guinea, Upper Niger",[(12.6,-8,2.4,4),(10,-11,1.6,2.5),(8.5,-11.5,1.2,2)]),
 ("mossi","Mossi and Voltaic peoples","Gur","Burkina Faso, northern Ghana",[(12.4,-1.5,2.2,2.6),(10,-1,1.2,2)]),
 ("wolof","Wolof and Senegambians","Atlantic","Senegal, Gambia",[(14.7,-16,2.2,2)]),
 ("fang","Fang and Cameroon peoples","Bantu","Cameroon, Gabon",[(4,11.5,2,3),(0,11.5,1.4,2.5),(6,11,1.4,2)]),
 ("kongo","Kongo and Lingala peoples","Bantu","Lower Congo, Kinshasa, Brazzaville",[(-4.3,15.3,2.6,3),(-6,14,1.6,2.5),(1,20,1,4)]),
 ("luba","Luba and Kasai peoples","Bantu","Kasai, Katanga",[(-6,23.5,2.2,4),(-10,26,1.4,3)]),
 ("mongo","Mongo and forest peoples","Bantu","Central Congo basin",[(-1,21,1.2,5)]),
 ("great_lakes","Great Lakes Bantu","Bantu","Uganda, Rwanda, Burundi, eastern Congo",[(0.5,32.5,2.4,2.8),(-2,29.8,2.4,1.6),(-1.5,28.5,1.3,2)]),
 ("swahili","Swahili and coastal Bantu","Bantu","Tanzania, Kenya coast",[(-6.5,35,2.2,5),(-4,39.5,1.5,2),(-3.4,36.7,1.4,2.5)]),
 ("kikuyu","Kikuyu and Kenyan highlanders","Bantu","Central Kenya, Lake Victoria shore",[(-0.6,37,2.2,2),(-0.3,34.7,1.6,1.5)]),
 ("nilotic","Nilotic peoples","Nilotic","South Sudan, Kenyan rift, Karamoja",[(7,31,2,4),(2,35.5,1.4,3)]),
 ("amhara","Amhara","Semitic","Ethiopian and Eritrean highlands",[(11.5,38.5,2.5,2.5),(14.5,39,1.6,1.8)]),
 ("oromo","Oromo","Cushitic","Southern and central Ethiopia",[(8,39,2.5,3),(9,36,1.4,2)]),
 ("somali","Somalis","Cushitic","Horn of Africa",[(5,46,2.2,5),(9.5,44,1.4,2.5),(1,42,1.3,2.5)]),
 ("sudanese","Sudanese Arabs and Nubians","Semitic","Middle Nile, Kordofan, Darfur",[(15.6,32.5,2.5,4),(13,25,1.5,4),(19,33,1.2,3)]),
 ("malagasy","Coastal Malagasy","Austronesian","Madagascar",[(-19,47,2.2,4)]),
 ("chewa","Chewa, Bemba and Zambezi peoples","Bantu","Malawi, Zambia",[(-13.5,33.8,2,2.5),(-13,28.5,1.8,3),(-15.4,28.3,1.3,2)]),
 ("makua","Makua and Mozambicans","Bantu","Northern and central Mozambique",[(-15,39,2,3),(-19,35,1.4,3)]),
 ("shona","Shona","Bantu","Zimbabwe",[(-18.5,31,2.4,3)]),
 ("ovimbundu","Ovimbundu and Angolans","Bantu","Angolan plateau",[(-12.5,16,2,3.5),(-9,14,1.4,2.5)]),
 ("ovambo","Ovambo and Namibians","Bantu","Northern and central Namibia",[(-18,16,2.2,2.5),(-22.5,17,1.4,3)]),
 ("tswana","Sotho-Tswana","Bantu","Highveld, Botswana, Lesotho",[(-26,27.5,2.4,3),(-24,25.5,1.2,3),(-29.5,28,1.5,1.3)]),
 ("zulu","Zulu and Nguni","Bantu","KwaZulu, Eswatini",[(-28.5,31,2.4,2.2),(-26.3,31.2,1.2,1)]),
 ("xhosa","Xhosa","Bantu","Eastern Cape",[(-32.5,27.5,2.2,2)]),
 ("afrikaner","Afrikaners and Cape coloureds","Germanic","Western and Northern Cape",[(-33.5,19.5,2,3),(-29,22,1,3)]),
 # ---- Americas
 ("anglo_am","Anglo-Americans","Germanic","United States interior; northward shift into a warmer Canada and Alaska",
  [(40,-89,3,8),(35,-97,2.2,6),(42,-75,2,4),(34,-84,2,4),(44,-110,1.2,8),(46,-122,1.5,3),(39.7,-105,1.4,3),(36,-115,1,3)]),
 ("african_am","African Americans","Afro-American","American South, northern cities",[(32.4,-87.5,3.4,2.6),(32.6,-84.2,3.0,2.0),(33.6,-80.8,2.8,1.8),(32.3,-90.5,2.8,1.8),(41.8,-87.6,1.8,0.6),(42.35,-83.1,1.8,0.5),(39.3,-76.6,1.5,0.6)]),
 ("canadian","Anglo-Canadians","Germanic","Ontario, Prairies, British Columbia; the new farm belt up to the Arctic Reach",[(44,-79.5,2,3),(50.5,-104,1.6,6),(53.5,-113.5,1.6,4),(49.5,-123,1.5,2.5),(57,-110,1,7)]),
 ("quebecois","Québécois","Romance","St Lawrence and the Laurentian north",[(46.8,-72,2.4,3.5),(49.5,-73,1.2,4)]),
 ("reacher","Reachers (Arctic Canadians)","2240 hybrid","New Canadians of the thawed north: Anglo, Québécois, South Asian, Filipino, Latin American and Inuit descent",[(62,-115,1.8,8),(58,-95,1.4,7),(64,-135,1.3,6),(68,-110,1.2,7),(66,-95,1.1,6),(69,-80,0.8,5)]),
 ("inuit","Inuit and Arctic natives","Eskimo-Aleut","Arctic coasts, Greenland, Alaska",[(68,-75,1,8),(70,-40,0.9,8),(64,-51.7,1,3),(66,-162,0.8,5),(72,-95,0.8,8)]),
 ("first_nations","First Nations and Native Americans","Indigenous American","Canadian Shield, Plains, Southwest",[(54,-95,1,8),(55,-122,0.8,5),(36,-109,1.2,3),(45,-101,0.6,4)]),
 ("alaskan","Alaskans","Germanic","Alaska interior, now farmed",[(62,-150,1.2,5)]),
 ("mexican","Mexicans (Mestizo)","Romance","Mexico; the US Southwest",[(19.4,-99.1,3,4),(21,-101.5,2.4,4),(25.7,-100.3,2,4),(29,-108,1.4,5),(34,-118.2,1.3,3),(21.3,-157.9,0.5,1.5),(29.4,-98.5,1.2,3),(33.5,-112,0.9,3),(41.9,-87.7,0.3,1.5)]),
 ("mesoamerican","Maya and Nahua peoples","Indigenous American","Southern Mexico, Guatemala",[(16.7,-92.6,2,2.5),(15,-91,1.8,2),(18,-97.5,1.3,2),(20.5,-89,1,2)]),
 ("centroamerican","Central Americans","Romance","Isthmus",[(13.8,-89,2,2),(14,-87,2,2),(12.5,-85.5,1.6,2),(9.9,-84,1.4,1.5),(8.5,-80,1.2,1.5)]),
 ("hisp_carib","Dominicans and Puerto Ricans","Romance","Eastern Hispaniola, Puerto Rico",[(19,-70.5,2,1.5),(18.2,-66.5,2.4,1)]),
 ("afro_carib","Lesser Antilleans and Bahamians","Afro-American","Lesser Antilles, Bahamas",[(13,-61,1.6,3),(24.5,-77.5,1.4,1.5)]),
 ("colombian","Colombians and Venezuelans","Romance","Andean north, Llanos",[(4.6,-74.1,2.6,3.5),(6.2,-75.6,2,2),(10.5,-66.9,2,2.5),(8,-64,1.3,3),(3.4,-76.5,1.4,2)]),
 ("andean","Andean Mestizos","Romance","Ecuador, Peru, Bolivia lowland cities",[(-0.7,-90.4,1.0,1.2),(-0.2,-78.5,2,2.5),(-12,-77,1.8,2.5),(-17.8,-63.2,1.6,3),(-8,-79,1.4,2)]),
 ("quechua","Quechua","Indigenous American","High Andes",[(-13.5,-72,2.2,3),(-16.5,-68.2,2,2.5),(-19.5,-66,1.4,2.5),(-2,-79,0.7,2)]),
 ("amazonian","Amazonian peoples","Indigenous American","Amazon forest",[(-4,-65,0.8,8),(-8,-58,0.6,7),(2,-62,0.6,5)]),
 ("brazilian","Brazilians","Romance","Brazil",[(-23.5,-46.6,3,4),(-22.9,-43.2,2.4,3),(-15.8,-47.9,2,4),(-19.9,-43.9,2,3),(-12.9,-38.5,2,3),(-8,-35,2,2.5),(-3.7,-38.5,1.6,3),(-25.4,-49.3,1.8,3),(-30,-51.2,1.6,3),(-3.1,-60,1,3),(-10,-50,0.9,6)]),
 ("guarani","Paraguayans and Guaraní","Romance","Paraguay",[(-25.3,-57.6,2,2.5)]),
 ("rioplatense","Rioplatenses","Romance","Argentina, Uruguay",[(-34.6,-58.4,2.6,3),(-32,-61,2,3),(-31.4,-64.2,1.8,3),(-34.9,-56.2,1.4,1.5),(-27,-65,1.2,3),(-40,-68,1,5)]),
 ("chilean","Chileans","Romance","Chile; the largest group on the Antarctic Peninsula",[(-33.4,-70.6,2.6,3),(-37,-72.5,1.8,2.5),(-41.5,-73,1.2,2.5),(-53,-71,0.8,3),(-64,-60,0.6,4)]),
 ("austral","Austral settlers (Antarctic)","2240 hybrid","Antarctic Trust settlers: Chilean, Argentine, Australian, New Zealand, South African and Chinese roots",[(-66,-62,1.0,4),(-67,100,0.7,5),(-72,168,0.7,5),(-69,35,0.6,5),(-77,-40,0.3,6)]),
]

# Mars: Martian-born identities dominate; Earth-origin communities from the
# settlement waves of 2060-2186 remain as minorities.
# seed lat/lon are areographic.
MARS = [
 ("m_tharsian","Tharsians","Martian","Tharsis highlands: the first terraforming crews' descendants, heart of the Sovereignty",[(0,-115,2.8,22),(15,-125,1.6,12),(-15,-105,1.6,12)]),
 ("m_marineris","Mariners (Valles folk)","Martian","Valles Marineris canyon cities, Lunae and Xanthe",[(-8,-70,2.6,14),(10,-60,1.4,12),(-5,-45,1.3,10)]),
 ("m_arabian","Arabians (Martian)","Martian","Arabia Terra, Meridiani: the old industrial belt seized from VANTEC in 2187",[(20,20,2.4,20),(0,0,2,14),(-10,-15,1.4,12)]),
 ("m_hellasian","Hellasians","Martian","Rim of the Hellas sea, Noachis, Hesperia",[(-40,70,2.3,18),(-20,105,1.6,14),(-45,30,1.3,14)]),
 ("m_elysian","Elysians","Martian","Elysium and Aeolis",[(20,145,2.2,16),(-5,140,1.5,12)]),
 ("m_boreal","Boreal coasters","Martian","Shores of the northern sea: fishing, kelp and shipping towns",[(45,-90,1.3,18),(45,40,1.3,18),(45,160,1.2,18),(60,-20,0.9,16)]),
 ("m_austral","Southern highlanders","Martian","Cimmeria, Sirenum, Aonia: thin, cold farm country",[(-35,-150,1.6,18),(-40,170,1.4,16),(-55,-60,1.1,16)]),
 # 0.1.25: four more Martian peoples, so Mars is not one Tharsian block
 ("m_olympian","Olympians","Martian","Olympus Mons and Amazonis: cliff-foot towns and the high spaceports on the great volcano",[(18,-134,2.6,9),(10,-150,1.4,8)]),
 ("m_utopian","Utopians","Martian","Utopia Planitia: the plain of the first northern farms, now a coast of the new sea",[(40,112,4.2,11),(30,122,2.2,8),(48,100,1.6,7)]),
 ("m_argyrian","Argyrians","Martian","Argyre basin: the walled lake country of the south",[(-50,-43,2.6,9),(-42,-30,1.2,7)]),
 ("m_isidian","Isidians","Martian","Isidis and Syrtis Major: the dark-sand plains between the old highlands and the sea",[(12,88,2.4,9),(8,70,1.3,8)]),
 # Earth-origin communities on Mars (by settlement wave)
 ("hannorth","Northern Han","Sinitic","Mars: first-wave Chinese agency crews",[(5,-120,1.8,4.8),(-10,-75,1.3,3.6)]),
 ("hindustani","Hindustanis (Hindi-Urdu)","Indo-Aryan","Mars: second-wave labour settlers",[(15,15,1.8,5.4),(-35,75,1.3,4.8)]),
 ("anglo_am","Anglo-Americans","Germanic","Mars: early PIONEER and VANTEC staff",[(-5,-60,1.3,4.2),(-3,-5,1.3,3.6)]),
 ("russian","Russians","Slavic","Mars: Arctic-trained crews of the 2090s",[(40,-100,1.3,4.8),(-50,-150,1.1,4.8)]),
 ("japanese","Japanese","Japonic","Mars: SYNTRIX automation towns",[(25,150,1.5,4.2)]),
 ("korean","Koreans","Koreanic","Mars: SYNTRIX and shipyard workers",[(-2,135,1.1,3.6)]),
 ("brazilian","Brazilians","Romance","Mars: GENETECH farm cooperatives",[(-40,95,1.3,4.8)]),
 ("yoruba","Yoruba","Volta-Niger","Mars: Lagos-founded trading towns",[(8,-30,1.1,4.2)]),
 ("levantine","Levantine Arabs","Semitic","Mars: Arabia Terra engineers",[(25,35,1.1,4.8)]),
 ("german","Germans","Germanic","Mars: VANTEC foundry towns, nationalised 2187",[(-5,10,1.1,3.6)]),
 ("mexican","Mexicans (Mestizo)","Romance","Mars: Hellas farm crews",[(-30,55,1.1,4.2)]),
]

from groups_more import EARTH_MORE
EARTH = EARTH + EARTH_MORE

# 0.1.8: 100 fusion peoples (two parent cultures each), urban and sprinkled worldwide.
from groups_fusion import FUSION
EARTH = EARTH + [f[:5] for f in FUSION]
FUSION_PARENTS = {f[0]: f[5] for f in FUSION}

# 0.1.15: Earth grows to 500 peoples.
from groups_500 import E500, FUSION_500
EARTH = EARTH + E500 + [f[:5] for f in FUSION_500]
FUSION_PARENTS.update({f[0]: f[5] for f in FUSION_500})

# Cores from calibrate_visibility.py: every people holds at least an enclave at its homeland.
try:
    from groups_cores import CORES
except ImportError:
    CORES = {}
EARTH = [(k, n, fam, note, list(seeds) + list(CORES.get(k, []))) for k, n, fam, note, seeds in EARTH]

# Hand-placed cores (checked on the 2240 water map) for peoples squeezed out by stronger neighbours.
MANUAL_CORES = {
    'lithuanian': [(54.7, 25.3, 4.0, 0.7)],       # Vilnius
    'pahari': [(31.1, 77.2, 4.0, 0.6)],           # Shimla
    'rohingya': [(21.2, 92.8, 3.5, 0.45)],        # hills above the drowned Arakan coast
    'salar_dongxiang': [(35.85, 102.5, 4.0, 0.5)],  # Xunhua
    'latvian': [(57.54, 25.43, 4.5, 0.7)],         # Valmiera
    'f_steppehan': [(40.84, 111.75, 4.5, 0.5)],    # Hohhot
    'mon': [(16.89, 97.63, 4.5, 0.5)],             # Hpa-an
    'mbundu': [(-9.54, 16.34, 4.5, 0.6)],          # Malanje
    'pedi': [(-23.9, 29.45, 4.5, 0.6)],            # Polokwane
    'rakhine': [(20.9, 93.6, 4.5, 0.7)],           # Arakan hills above the drowned coast (0.1.22)
    'f_tatarrus': [(55.8, 49.1, 3.0, 0.5)],         # Kazan
    'f_turcogerman': [(51.85, 13.4, 3.0, 0.45)],    # the shore south of drowned Berlin
    'indo_trini': [(10.63, -63.28, 4.5, 0.5)],      # Paria coast, where drowned Trinidad's people went
}
EARTH = [(k, n, fam, note, list(seeds) + list(MANUAL_CORES.get(k, []))) for k, n, fam, note, seeds in EARTH]
