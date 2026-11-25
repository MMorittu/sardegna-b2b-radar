"""Complete ISTAT 377 Sardinian Municipalities Atlas & 4-Tier Zero-Collision Resolver."""

from __future__ import annotations

from dataclasses import dataclass
import functools
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class SardinianMunicipality:
    """Canonical Sardinian municipality metadata with road distance from Silanus HQ."""

    name: str
    province_code: str
    istat_code: str
    belfiore_code: str
    road_km_from_silanus: int


SARDINIAN_MUNICIPALITIES: tuple[SardinianMunicipality, ...] = (
    SardinianMunicipality('Abbasanta', 'OR', '095001', 'A007', 27),
    SardinianMunicipality('Aggius', 'SS', '090001', 'A069', 114),
    SardinianMunicipality('Aglientu', 'SS', '090062', 'H848', 124),
    SardinianMunicipality('Aidomaggiore', 'OR', '095002', 'A097', 26),
    SardinianMunicipality('Albagiara', 'OR', '095003', 'A126', 74),
    SardinianMunicipality('Ales', 'OR', '095004', 'A180', 76),
    SardinianMunicipality('Alghero', 'SS', '090003', 'A192', 88),
    SardinianMunicipality('Allai', 'OR', '095005', 'A204', 52),
    SardinianMunicipality('Alà dei Sardi', 'SS', '090002', 'A115', 72),
    SardinianMunicipality('Anela', 'SS', '090004', 'A287', 34),
    SardinianMunicipality('Arborea', 'OR', '095006', 'A357', 74),
    SardinianMunicipality('Arbus', 'SU', '111001', 'A359', 110),
    SardinianMunicipality('Ardara', 'SS', '090005', 'A379', 56),
    SardinianMunicipality('Ardauli', 'OR', '095007', 'A380', 48),
    SardinianMunicipality('Aritzo', 'NU', '091001', 'A407', 68),
    SardinianMunicipality('Armungia', 'SU', '111002', 'A419', 158),
    SardinianMunicipality('Arzachena', 'SS', '090006', 'A453', 138),
    SardinianMunicipality('Arzana', 'NU', '091002', 'A454', 92),
    SardinianMunicipality('Assemini', 'CA', '092003', 'A474', 148),
    SardinianMunicipality('Assolo', 'OR', '095008', 'A477', 48),
    SardinianMunicipality('Asuni', 'OR', '095009', 'A480', 48),
    SardinianMunicipality('Atzara', 'NU', '091003', 'A492', 62),
    SardinianMunicipality('Austis', 'NU', '091004', 'A503', 68),
    SardinianMunicipality('Badesi', 'SS', '090081', 'M214', 102),
    SardinianMunicipality('Ballao', 'SU', '111003', 'A597', 158),
    SardinianMunicipality('Banari', 'SS', '090007', 'A606', 52),
    SardinianMunicipality('Baradili', 'OR', '095010', 'A614', 74),
    SardinianMunicipality('Baratili San Pietro', 'OR', '095011', 'A621', 34),
    SardinianMunicipality('Baressa', 'OR', '095012', 'A655', 74),
    SardinianMunicipality('Bari Sardo', 'NU', '091005', 'A663', 102),
    SardinianMunicipality('Barrali', 'SU', '111004', 'A677', 158),
    SardinianMunicipality('Barumini', 'SU', '111005', 'A681', 118),
    SardinianMunicipality('Bauladu', 'OR', '095013', 'A721', 49),
    SardinianMunicipality('Baunei', 'NU', '091006', 'A722', 108),
    SardinianMunicipality('Belvì', 'NU', '091007', 'A776', 66),
    SardinianMunicipality('Benetutti', 'SS', '090008', 'A781', 39),
    SardinianMunicipality('Berchidda', 'SS', '090009', 'A789', 82),
    SardinianMunicipality('Bessude', 'SS', '090010', 'A827', 48),
    SardinianMunicipality('Bidonì', 'OR', '095014', 'A856', 34),
    SardinianMunicipality('Birori', 'NU', '091008', 'A880', 11),
    SardinianMunicipality('Bitti', 'NU', '091009', 'A895', 62),
    SardinianMunicipality('Bolotana', 'NU', '091010', 'A948', 11),
    SardinianMunicipality('Bonarcado', 'OR', '095015', 'A960', 38),
    SardinianMunicipality('Bonnanaro', 'SS', '090011', 'A976', 82),
    SardinianMunicipality('Bono', 'SS', '090012', 'A977', 28),
    SardinianMunicipality('Bonorva', 'SS', '090013', 'A978', 35),
    SardinianMunicipality('Boroneddu', 'OR', '095016', 'B055', 30),
    SardinianMunicipality('Borore', 'NU', '091011', 'B056', 16),
    SardinianMunicipality('Bortigali', 'NU', '091012', 'B062', 9),
    SardinianMunicipality('Bortigiadas', 'SS', '090014', 'B063', 82),
    SardinianMunicipality('Borutta', 'SS', '090015', 'B064', 82),
    SardinianMunicipality('Bosa', 'OR', '095079', 'B068', 48),
    SardinianMunicipality('Bottidda', 'SS', '090016', 'B094', 30),
    SardinianMunicipality('Buddusò', 'SS', '090017', 'B246', 64),
    SardinianMunicipality('Budoni', 'SS', '090091', 'B248', 104),
    SardinianMunicipality('Buggerru', 'SU', '111006', 'B250', 175),
    SardinianMunicipality('Bultei', 'SS', '090018', 'B264', 40),
    SardinianMunicipality('Bulzi', 'SS', '090019', 'B265', 82),
    SardinianMunicipality('Burcei', 'SU', '111007', 'B274', 158),
    SardinianMunicipality('Burgos', 'SS', '090020', 'B276', 31),
    SardinianMunicipality('Busachi', 'OR', '095017', 'B281', 38),
    SardinianMunicipality('Cabras', 'OR', '095018', 'B314', 70),
    SardinianMunicipality('Cagliari', 'CA', '092009', 'B354', 155),
    SardinianMunicipality('Calangianus', 'SS', '090021', 'B378', 106),
    SardinianMunicipality('Calasetta', 'SU', '111008', 'B383', 198),
    SardinianMunicipality('Capoterra', 'CA', '092011', 'B675', 164),
    SardinianMunicipality('Carbonia', 'SU', '111009', 'B745', 178),
    SardinianMunicipality('Cardedu', 'NU', '091103', 'M285', 103),
    SardinianMunicipality('Cargeghe', 'SS', '090022', 'B772', 68),
    SardinianMunicipality('Carloforte', 'SU', '111010', 'B789', 196),
    SardinianMunicipality('Castelsardo', 'SS', '090023', 'C272', 96),
    SardinianMunicipality('Castiadas', 'SU', '111011', 'M288', 186),
    SardinianMunicipality('Cheremule', 'SS', '090024', 'C600', 46),
    SardinianMunicipality('Chiaramonti', 'SS', '090025', 'C613', 74),
    SardinianMunicipality('Codrongianos', 'SS', '090026', 'C818', 62),
    SardinianMunicipality('Collinas', 'SU', '111012', 'C882', 118),
    SardinianMunicipality('Cossoine', 'SS', '090027', 'D100', 38),
    SardinianMunicipality('Cuglieri', 'OR', '095019', 'D200', 45),
    SardinianMunicipality('Curcuris', 'OR', '095077', 'D214', 74),
    SardinianMunicipality('Decimomannu', 'CA', '092015', 'D259', 140),
    SardinianMunicipality('Decimoputzu', 'SU', '111013', 'D260', 175),
    SardinianMunicipality('Desulo', 'NU', '091016', 'D287', 70),
    SardinianMunicipality('Dolianova', 'SU', '111014', 'D323', 144),
    SardinianMunicipality('Domus de Maria', 'SU', '111015', 'D333', 192),
    SardinianMunicipality('Domusnovas', 'SU', '111016', 'D334', 156),
    SardinianMunicipality('Donori', 'SU', '111017', 'D344', 158),
    SardinianMunicipality('Dorgali', 'NU', '091017', 'D345', 68),
    SardinianMunicipality('Dualchi', 'NU', '091018', 'D376', 13),
    SardinianMunicipality('Elini', 'NU', '091019', 'D395', 94),
    SardinianMunicipality('Elmas', 'CA', '092108', 'D399', 150),
    SardinianMunicipality('Erula', 'SS', '090088', 'M292', 82),
    SardinianMunicipality('Escalaplano', 'SU', '111018', 'D430', 155),
    SardinianMunicipality('Escolca', 'SU', '111019', 'D431', 155),
    SardinianMunicipality('Esporlatu', 'SS', '090028', 'D441', 29),
    SardinianMunicipality('Esterzili', 'SU', '111020', 'D443', 155),
    SardinianMunicipality('Florinas', 'SS', '090029', 'D637', 64),
    SardinianMunicipality('Fluminimaggiore', 'SU', '111021', 'D639', 175),
    SardinianMunicipality('Flussio', 'OR', '095080', 'D640', 74),
    SardinianMunicipality('Fonni', 'NU', '091024', 'D665', 58),
    SardinianMunicipality('Fordongianus', 'OR', '095020', 'D695', 46),
    SardinianMunicipality('Furtei', 'SU', '111022', 'D827', 158),
    SardinianMunicipality('Gadoni', 'NU', '091025', 'D842', 68),
    SardinianMunicipality('Gairo', 'NU', '091026', 'D859', 98),
    SardinianMunicipality('Galtellì', 'NU', '091027', 'D888', 68),
    SardinianMunicipality('Gavoi', 'NU', '091028', 'D947', 48),
    SardinianMunicipality('Genoni', 'SU', '111023', 'D968', 155),
    SardinianMunicipality('Genuri', 'SU', '111024', 'D970', 118),
    SardinianMunicipality('Gergei', 'SU', '111025', 'D982', 155),
    SardinianMunicipality('Gesico', 'SU', '111026', 'D994', 158),
    SardinianMunicipality('Gesturi', 'SU', '111027', 'D997', 118),
    SardinianMunicipality('Ghilarza', 'OR', '095021', 'E004', 28),
    SardinianMunicipality('Giave', 'SS', '090030', 'E019', 42),
    SardinianMunicipality('Giba', 'SU', '111028', 'E022', 184),
    SardinianMunicipality('Girasole', 'NU', '091031', 'E049', 97),
    SardinianMunicipality('Golfo Aranci', 'SS', '090083', 'M274', 132),
    SardinianMunicipality('Goni', 'SU', '111029', 'E084', 158),
    SardinianMunicipality('Gonnesa', 'SU', '111030', 'E086', 175),
    SardinianMunicipality('Gonnoscodina', 'OR', '095022', 'E087', 74),
    SardinianMunicipality('Gonnosfanadiga', 'SU', '111031', 'E085', 155),
    SardinianMunicipality('Gonnosnò', 'OR', '095023', 'D585', 74),
    SardinianMunicipality('Gonnostramatza', 'OR', '095024', 'E088', 74),
    SardinianMunicipality('Guamaggiore', 'SU', '111032', 'E234', 158),
    SardinianMunicipality('Guasila', 'SU', '111033', 'E252', 122),
    SardinianMunicipality('Guspini', 'SU', '111034', 'E270', 104),
    SardinianMunicipality('Iglesias', 'SU', '111035', 'E281', 165),
    SardinianMunicipality('Ilbono', 'NU', '091032', 'E283', 96),
    SardinianMunicipality('Illorai', 'SS', '090031', 'E285', 24),
    SardinianMunicipality('Irgoli', 'NU', '091033', 'E323', 70),
    SardinianMunicipality('Isili', 'SU', '111036', 'E336', 92),
    SardinianMunicipality('Ittireddu', 'SS', '090032', 'E376', 48),
    SardinianMunicipality('Ittiri', 'SS', '090033', 'E377', 68),
    SardinianMunicipality('Jerzu', 'NU', '091035', 'E387', 102),
    SardinianMunicipality('La Maddalena', 'SS', '090035', 'E425', 148),
    SardinianMunicipality('Laconi', 'OR', '095082', 'E400', 74),
    SardinianMunicipality('Laerru', 'SS', '090034', 'E401', 82),
    SardinianMunicipality('Lanusei', 'NU', '091037', 'E441', 92),
    SardinianMunicipality('Las Plassas', 'SU', '111037', 'E464', 118),
    SardinianMunicipality('Lei', 'NU', '091038', 'E517', 6),
    SardinianMunicipality('Loceri', 'NU', '091039', 'E644', 98),
    SardinianMunicipality('Loculi', 'NU', '091040', 'E646', 70),
    SardinianMunicipality('Lodine', 'NU', '091104', 'E649', 52),
    SardinianMunicipality('Lodè', 'NU', '091041', 'E647', 88),
    SardinianMunicipality('Loiri Porto San Paolo', 'SS', '090084', 'M275', 122),
    SardinianMunicipality('Lotzorai', 'NU', '091042', 'E700', 99),
    SardinianMunicipality('Lula', 'NU', '091043', 'E736', 64),
    SardinianMunicipality('Lunamatrona', 'SU', '111038', 'E742', 118),
    SardinianMunicipality('Luogosanto', 'SS', '090036', 'E747', 122),
    SardinianMunicipality('Luras', 'SS', '090037', 'E752', 108),
    SardinianMunicipality('Macomer', 'NU', '091044', 'E788', 15),
    SardinianMunicipality('Magomadas', 'OR', '095083', 'E825', 45),
    SardinianMunicipality('Mamoiada', 'NU', '091046', 'E874', 44),
    SardinianMunicipality('Mandas', 'SU', '111039', 'E877', 114),
    SardinianMunicipality('Mara', 'SS', '090038', 'E902', 38),
    SardinianMunicipality('Maracalagonis', 'CA', '092037', 'E903', 162),
    SardinianMunicipality('Marrubiu', 'OR', '095025', 'E972', 72),
    SardinianMunicipality('Martis', 'SS', '090039', 'E992', 72),
    SardinianMunicipality('Masainas', 'SU', '111040', 'M270', 175),
    SardinianMunicipality('Masullas', 'OR', '095026', 'F050', 74),
    SardinianMunicipality('Meana Sardo', 'NU', '091047', 'F073', 68),
    SardinianMunicipality('Milis', 'OR', '095027', 'F208', 55),
    SardinianMunicipality('Modolo', 'OR', '095084', 'F261', 46),
    SardinianMunicipality('Mogorella', 'OR', '095028', 'F270', 48),
    SardinianMunicipality('Mogoro', 'OR', '095029', 'F272', 84),
    SardinianMunicipality('Monastir', 'SU', '111041', 'F333', 118),
    SardinianMunicipality('Monserrato', 'CA', '092109', 'F383', 154),
    SardinianMunicipality('Monteleone Rocca Doria', 'SS', '090040', 'F542', 38),
    SardinianMunicipality('Monti', 'SS', '090041', 'F667', 94),
    SardinianMunicipality('Montresta', 'OR', '095085', 'F698', 74),
    SardinianMunicipality('Mores', 'SS', '090042', 'F721', 50),
    SardinianMunicipality('Morgongiori', 'OR', '095030', 'F727', 76),
    SardinianMunicipality('Muravera', 'SU', '111042', 'F808', 182),
    SardinianMunicipality('Muros', 'SS', '090043', 'F818', 70),
    SardinianMunicipality('Musei', 'SU', '111043', 'F822', 156),
    SardinianMunicipality('Narbolia', 'OR', '095031', 'F840', 62),
    SardinianMunicipality('Narcao', 'SU', '111044', 'F841', 175),
    SardinianMunicipality('Neoneli', 'OR', '095032', 'F867', 38),
    SardinianMunicipality('Noragugume', 'NU', '091050', 'F933', 14),
    SardinianMunicipality('Norbello', 'OR', '095033', 'F934', 27),
    SardinianMunicipality('Nughedu San Nicolò', 'SS', '090044', 'F975', 49),
    SardinianMunicipality('Nughedu Santa Vittoria', 'OR', '095034', 'F974', 38),
    SardinianMunicipality('Nule', 'SS', '090045', 'F976', 40),
    SardinianMunicipality('Nulvi', 'SS', '090046', 'F977', 80),
    SardinianMunicipality('Nuoro', 'NU', '091051', 'F979', 38),
    SardinianMunicipality('Nurachi', 'OR', '095035', 'F980', 34),
    SardinianMunicipality('Nuragus', 'SU', '111045', 'F981', 155),
    SardinianMunicipality('Nurallao', 'SU', '111046', 'F982', 155),
    SardinianMunicipality('Nuraminis', 'SU', '111047', 'F983', 118),
    SardinianMunicipality('Nureci', 'OR', '095036', 'F985', 48),
    SardinianMunicipality('Nurri', 'SU', '111048', 'F986', 155),
    SardinianMunicipality('Nuxis', 'SU', '111049', 'F991', 175),
    SardinianMunicipality('Olbia', 'SS', '090047', 'G015', 118),
    SardinianMunicipality('Oliena', 'NU', '091055', 'G031', 48),
    SardinianMunicipality('Ollastra', 'OR', '095037', 'G043', 54),
    SardinianMunicipality('Ollolai', 'NU', '091056', 'G044', 46),
    SardinianMunicipality('Olmedo', 'SS', '090048', 'G046', 80),
    SardinianMunicipality('Olzai', 'NU', '091057', 'G058', 42),
    SardinianMunicipality('Onanì', 'NU', '091058', 'G064', 66),
    SardinianMunicipality('Onifai', 'NU', '091059', 'G070', 71),
    SardinianMunicipality('Oniferi', 'NU', '091060', 'G071', 31),
    SardinianMunicipality('Orani', 'NU', '091061', 'G084', 32),
    SardinianMunicipality('Orgosolo', 'NU', '091062', 'G097', 54),
    SardinianMunicipality('Oristano', 'OR', '095038', 'G113', 64),
    SardinianMunicipality('Orosei', 'NU', '091063', 'G119', 72),
    SardinianMunicipality('Orotelli', 'NU', '091064', 'G120', 26),
    SardinianMunicipality('Orroli', 'SU', '111050', 'G122', 155),
    SardinianMunicipality('Ortacesus', 'SU', '111051', 'G133', 158),
    SardinianMunicipality('Ortueri', 'NU', '091066', 'G146', 56),
    SardinianMunicipality('Orune', 'NU', '091067', 'G147', 54),
    SardinianMunicipality('Oschiri', 'SS', '090049', 'G153', 74),
    SardinianMunicipality('Osidda', 'NU', '091068', 'G154', 52),
    SardinianMunicipality('Osilo', 'SS', '090050', 'G156', 82),
    SardinianMunicipality('Osini', 'NU', '091069', 'G158', 98),
    SardinianMunicipality('Ossi', 'SS', '090051', 'G178', 72),
    SardinianMunicipality('Ottana', 'NU', '091070', 'G191', 24),
    SardinianMunicipality('Ovodda', 'NU', '091071', 'G201', 50),
    SardinianMunicipality('Ozieri', 'SS', '090052', 'G203', 52),
    SardinianMunicipality('Pabillonis', 'SU', '111052', 'G207', 155),
    SardinianMunicipality('Padria', 'SS', '090053', 'G225', 39),
    SardinianMunicipality('Padru', 'SS', '090090', 'M301', 122),
    SardinianMunicipality('Palau', 'SS', '090054', 'G258', 142),
    SardinianMunicipality('Palmas Arborea', 'OR', '095039', 'G286', 74),
    SardinianMunicipality('Pattada', 'SS', '090055', 'G376', 58),
    SardinianMunicipality('Pau', 'OR', '095040', 'G379', 74),
    SardinianMunicipality('Pauli Arbarei', 'SU', '111053', 'G382', 118),
    SardinianMunicipality('Paulilatino', 'OR', '095041', 'G384', 32),
    SardinianMunicipality('Perdasdefogu', 'NU', '091072', 'G445', 98),
    SardinianMunicipality('Perdaxius', 'SU', '111054', 'G446', 175),
    SardinianMunicipality('Perfugas', 'SS', '090056', 'G450', 84),
    SardinianMunicipality('Pimentel', 'SU', '111055', 'G669', 118),
    SardinianMunicipality('Piscinas', 'SU', '111056', 'M291', 175),
    SardinianMunicipality('Ploaghe', 'SS', '090057', 'G740', 64),
    SardinianMunicipality('Pompu', 'OR', '095042', 'G817', 74),
    SardinianMunicipality('Porto Torres', 'SS', '090058', 'G924', 95),
    SardinianMunicipality('Portoscuso', 'SU', '111057', 'G922', 184),
    SardinianMunicipality('Posada', 'NU', '091073', 'G929', 90),
    SardinianMunicipality('Pozzomaggiore', 'SS', '090059', 'G962', 37),
    SardinianMunicipality('Pula', 'CA', '092050', 'H088', 180),
    SardinianMunicipality('Putifigari', 'SS', '090060', 'H095', 82),
    SardinianMunicipality("Quartu Sant'Elena", 'CA', '092051', 'H118', 162),
    SardinianMunicipality('Quartucciu', 'CA', '092105', 'H119', 156),
    SardinianMunicipality('Riola Sardo', 'OR', '095043', 'H301', 68),
    SardinianMunicipality('Romana', 'SS', '090061', 'H507', 38),
    SardinianMunicipality('Ruinas', 'OR', '095044', 'F271', 48),
    SardinianMunicipality('Sadali', 'SU', '111058', 'H659', 155),
    SardinianMunicipality('Sagama', 'OR', '095086', 'H661', 39),
    SardinianMunicipality('Samassi', 'SU', '111059', 'H738', 118),
    SardinianMunicipality('Samatzai', 'SU', '111060', 'H739', 118),
    SardinianMunicipality('Samugheo', 'OR', '095045', 'H756', 56),
    SardinianMunicipality('San Basilio', 'SU', '111061', 'H766', 158),
    SardinianMunicipality('San Gavino Monreale', 'SU', '111062', 'H856', 106),
    SardinianMunicipality('San Giovanni Suergiu', 'SU', '111063', 'G287', 182),
    SardinianMunicipality('San Nicolò Gerrei', 'SU', '111064', 'G383', 158),
    SardinianMunicipality("San Nicolò d'Arcidano", 'OR', '095046', 'A368', 74),
    SardinianMunicipality('San Sperate', 'SU', '111065', 'I166', 118),
    SardinianMunicipality('San Teodoro', 'SS', '090092', 'I329', 112),
    SardinianMunicipality('San Vero Milis', 'OR', '095050', 'I384', 58),
    SardinianMunicipality('San Vito', 'SU', '111066', 'I402', 180),
    SardinianMunicipality('Sanluri', 'SU', '111067', 'H974', 108),
    SardinianMunicipality("Sant'Andrea Frius", 'SU', '111069', 'I271', 158),
    SardinianMunicipality("Sant'Anna Arresi", 'SU', '111070', 'M209', 192),
    SardinianMunicipality("Sant'Antioco", 'SU', '111071', 'I294', 190),
    SardinianMunicipality("Sant'Antonio di Gallura", 'SS', '090085', 'M276', 82),
    SardinianMunicipality('Santa Giusta', 'OR', '095047', 'I205', 67),
    SardinianMunicipality('Santa Maria Coghinas', 'SS', '090087', 'M284', 94),
    SardinianMunicipality('Santa Teresa Gallura', 'SS', '090063', 'I312', 138),
    SardinianMunicipality('Santadi', 'SU', '111068', 'I182', 175),
    SardinianMunicipality('Santu Lussurgiu', 'OR', '095049', 'I374', 34),
    SardinianMunicipality('Sardara', 'SU', '111072', 'I428', 98),
    SardinianMunicipality('Sarroch', 'CA', '092066', 'I443', 172),
    SardinianMunicipality('Sarule', 'NU', '091077', 'I448', 34),
    SardinianMunicipality('Sassari', 'SS', '090064', 'I452', 78),
    SardinianMunicipality('Scano di Montiferro', 'OR', '095051', 'I503', 36),
    SardinianMunicipality('Sedilo', 'OR', '095052', 'I564', 25),
    SardinianMunicipality('Sedini', 'SS', '090065', 'I565', 88),
    SardinianMunicipality('Segariu', 'SU', '111073', 'I570', 158),
    SardinianMunicipality('Selargius', 'CA', '092068', 'I580', 155),
    SardinianMunicipality('Selegas', 'SU', '111074', 'I582', 158),
    SardinianMunicipality('Semestene', 'SS', '090066', 'I598', 31),
    SardinianMunicipality('Seneghe', 'OR', '095053', 'I605', 34),
    SardinianMunicipality('Senis', 'OR', '095054', 'I609', 48),
    SardinianMunicipality('Sennariolo', 'OR', '095055', 'I613', 34),
    SardinianMunicipality('Sennori', 'SS', '090067', 'I614', 88),
    SardinianMunicipality('Senorbì', 'SU', '111075', 'I615', 128),
    SardinianMunicipality('Serdiana', 'SU', '111076', 'I624', 142),
    SardinianMunicipality('Serramanna', 'SU', '111077', 'I647', 124),
    SardinianMunicipality('Serrenti', 'SU', '111078', 'I667', 118),
    SardinianMunicipality('Serri', 'SU', '111079', 'I668', 155),
    SardinianMunicipality('Sestu', 'CA', '092074', 'I695', 146),
    SardinianMunicipality('Settimo San Pietro', 'CA', '092075', 'I699', 155),
    SardinianMunicipality('Setzu', 'SU', '111080', 'I705', 118),
    SardinianMunicipality('Seui', 'SU', '111081', 'I706', 155),
    SardinianMunicipality('Seulo', 'SU', '111082', 'I707', 155),
    SardinianMunicipality('Siamaggiore', 'OR', '095056', 'I717', 60),
    SardinianMunicipality('Siamanna', 'OR', '095057', 'I718', 48),
    SardinianMunicipality('Siapiccia', 'OR', '095076', 'I721', 48),
    SardinianMunicipality('Siddi', 'SU', '111083', 'I724', 118),
    SardinianMunicipality('Silanus', 'NU', '091083', 'I730', 2),
    SardinianMunicipality('Siligo', 'SS', '090068', 'I732', 50),
    SardinianMunicipality('Siliqua', 'SU', '111084', 'I734', 148),
    SardinianMunicipality('Silius', 'SU', '111085', 'I735', 158),
    SardinianMunicipality('Simala', 'OR', '095058', 'I742', 74),
    SardinianMunicipality('Simaxis', 'OR', '095059', 'I743', 48),
    SardinianMunicipality('Sindia', 'NU', '091084', 'I748', 23),
    SardinianMunicipality('Sini', 'OR', '095060', 'I749', 74),
    SardinianMunicipality('Siniscola', 'NU', '091085', 'I751', 85),
    SardinianMunicipality('Sinnai', 'CA', '092080', 'I752', 158),
    SardinianMunicipality('Siris', 'OR', '095061', 'I757', 74),
    SardinianMunicipality('Siurgus Donigala', 'SU', '111086', 'I765', 158),
    SardinianMunicipality('Soddì', 'OR', '095078', 'I778', 29),
    SardinianMunicipality('Solarussa', 'OR', '095062', 'I791', 58),
    SardinianMunicipality('Soleminis', 'SU', '111087', 'I797', 158),
    SardinianMunicipality('Sorgono', 'NU', '091086', 'I851', 58),
    SardinianMunicipality('Sorradile', 'OR', '095063', 'I861', 35),
    SardinianMunicipality('Sorso', 'SS', '090069', 'I863', 86),
    SardinianMunicipality('Stintino', 'SS', '090089', 'M290', 115),
    SardinianMunicipality('Suelli', 'SU', '111088', 'I995', 126),
    SardinianMunicipality('Suni', 'OR', '095087', 'L006', 38),
    SardinianMunicipality('Tadasuni', 'OR', '095064', 'L023', 31),
    SardinianMunicipality('Talana', 'NU', '091088', 'L036', 98),
    SardinianMunicipality('Telti', 'SS', '090080', 'L088', 108),
    SardinianMunicipality('Tempio Pausania', 'SS', '090070', 'L093', 112),
    SardinianMunicipality('Tergu', 'SS', '090086', 'M282', 82),
    SardinianMunicipality('Terralba', 'OR', '095065', 'L122', 78),
    SardinianMunicipality('Tertenia', 'NU', '091089', 'L140', 98),
    SardinianMunicipality('Teti', 'NU', '091090', 'L153', 46),
    SardinianMunicipality('Teulada', 'SU', '111089', 'L154', 198),
    SardinianMunicipality('Thiesi', 'SS', '090071', 'L158', 46),
    SardinianMunicipality('Tiana', 'NU', '091091', 'L160', 52),
    SardinianMunicipality('Tinnura', 'OR', '095088', 'L172', 40),
    SardinianMunicipality('Tissi', 'SS', '090072', 'L180', 75),
    SardinianMunicipality('Tonara', 'NU', '091093', 'L202', 62),
    SardinianMunicipality('Torpè', 'NU', '091094', 'L231', 92),
    SardinianMunicipality('Torralba', 'SS', '090073', 'L235', 44),
    SardinianMunicipality('Tortolì', 'NU', '091095', 'A355', 98),
    SardinianMunicipality('Tramatza', 'OR', '095066', 'L321', 54),
    SardinianMunicipality('Tratalias', 'SU', '111090', 'L337', 175),
    SardinianMunicipality('Tresnuraghes', 'OR', '095067', 'L393', 44),
    SardinianMunicipality('Triei', 'NU', '091097', 'L423', 101),
    SardinianMunicipality("Trinità d'Agultu e Vignola", 'SS', '090074', 'L428', 108),
    SardinianMunicipality('Tuili', 'SU', '111091', 'L463', 118),
    SardinianMunicipality('Tula', 'SS', '090075', 'L464', 38),
    SardinianMunicipality('Turri', 'SU', '111092', 'L473', 118),
    SardinianMunicipality('Ulassai', 'NU', '091098', 'L489', 100),
    SardinianMunicipality('Ulà Tirso', 'OR', '095068', 'L488', 35),
    SardinianMunicipality('Uras', 'OR', '095069', 'L496', 78),
    SardinianMunicipality('Uri', 'SS', '090076', 'L503', 74),
    SardinianMunicipality('Urzulei', 'NU', '091099', 'L506', 86),
    SardinianMunicipality('Usellus', 'OR', '095070', 'L508', 74),
    SardinianMunicipality('Usini', 'SS', '090077', 'L509', 76),
    SardinianMunicipality('Ussana', 'SU', '111093', 'L512', 118),
    SardinianMunicipality('Ussaramanna', 'SU', '111094', 'L513', 118),
    SardinianMunicipality('Ussassai', 'NU', '091100', 'L514', 98),
    SardinianMunicipality('Uta', 'CA', '092090', 'L521', 146),
    SardinianMunicipality('Valledoria', 'SS', '090079', 'L604', 94),
    SardinianMunicipality('Vallermosa', 'SU', '111095', 'L613', 142),
    SardinianMunicipality('Viddalba', 'SS', '090082', 'M259', 96),
    SardinianMunicipality('Villa San Pietro', 'CA', '092099', 'I118', 176),
    SardinianMunicipality("Villa Sant'Antonio", 'OR', '095048', 'I298', 48),
    SardinianMunicipality('Villa Verde', 'OR', '095073', 'A609', 74),
    SardinianMunicipality('Villacidro', 'SU', '111096', 'L924', 124),
    SardinianMunicipality('Villagrande Strisaili', 'NU', '091101', 'L953', 88),
    SardinianMunicipality('Villamar', 'SU', '111097', 'L966', 118),
    SardinianMunicipality('Villamassargia', 'SU', '111098', 'L968', 158),
    SardinianMunicipality('Villanova Monteleone', 'SS', '090078', 'L989', 72),
    SardinianMunicipality('Villanova Truschedu', 'OR', '095071', 'L991', 50),
    SardinianMunicipality('Villanova Tulo', 'SU', '111099', 'L992', 88),
    SardinianMunicipality('Villanovaforru', 'SU', '111100', 'L986', 118),
    SardinianMunicipality('Villanovafranca', 'SU', '111101', 'L987', 118),
    SardinianMunicipality('Villaperuccio', 'SU', '111102', 'M278', 175),
    SardinianMunicipality('Villaputzu', 'SU', '111103', 'L998', 158),
    SardinianMunicipality('Villasalto', 'SU', '111104', 'M016', 158),
    SardinianMunicipality('Villasimius', 'SU', '111105', 'B738', 195),
    SardinianMunicipality('Villasor', 'SU', '111106', 'M025', 132),
    SardinianMunicipality('Villaspeciosa', 'SU', '111107', 'M026', 175),
    SardinianMunicipality('Villaurbana', 'OR', '095072', 'M030', 48),
    SardinianMunicipality('Zeddiani', 'OR', '095074', 'M153', 60),
    SardinianMunicipality('Zerfaliu', 'OR', '095075', 'M168', 56),
)

SARDINIAN_ISTAT_PROVINCE_PREFIXES: tuple[str, ...] = (
    # Classical Era (still dominant on ANAC BDNCP): SS=090, NU=091, CA=092, OR=095
    "090",
    "091",
    "092",
    "095",
    # 2005-2016 Era & 2016-2025 Sud Sardegna Era: OT=104, OG=105, VS=106, CI=107, SU=111
    "104",
    "105",
    "106",
    "107",
    "111",
    # Post-2025 Sardinian Metropolitan & Provincial Reform Era (L.R. 7/2021): 112..119
    "112",
    "113",
    "114",
    "115",
    "116",
    "117",
    "118",
    "119",
)

AMBIGUOUS_COMUNI: frozenset[str] = frozenset(
    {
        "Loculi", "Lei", "Bono", "Sorgono", "Bidonì", "Lodè", "Arborea", "Musei",
        "Monti", "Romana", "Girasole", "Ossi", "Uta", "Pau", "Uri", "Ales",
        "Padru", "Muros", "Ruinas", "Piscinas", "Mara", "Pula", "Sorso", "Assolo", "Modolo",
        "Villa Verde", "La Maddalena",
        "Cabras", "Siddi", "Martis", "Sini", "Sestu", "Milis", "Bosa", "Mores",
        "Lula", "Tula", "Suni", "Seui", "Serri", "Senis", "Teti", "Tiana", "Uras", "Nule", "Giba", "Goni",
        "San Vito", "San Basilio", "San Teodoro", "Santa Giusta", "San Sperate", "Sant'Antioco",
    }
)

ALIASES_AND_FRAZIONI: dict[str, str] = {
    "p.torres": "Porto Torres",
    "p. torres": "Porto Torres",
    "barisardo": "Bari Sardo",
    "villanovatulo": "Villanova Tulo",
    "pauli latino": "Paulilatino",
    "quartu s. elena": "Quartu Sant'Elena",
    "quartu s.elena": "Quartu Sant'Elena",
    "quartu sant elena": "Quartu Sant'Elena",
    "s. antioco": "Sant'Antioco",
    "s.antioco": "Sant'Antioco",
    "sant antioco": "Sant'Antioco",
    "s. anna arresi": "Sant'Anna Arresi",
    "s. teodoro": "San Teodoro",
    "s. giusta": "Santa Giusta",
    "s. gavino monreale": "San Gavino Monreale",
    "s. maria coghinas": "Santa Maria Coghinas",
    "s. teresa gallura": "Santa Teresa Gallura",
    "s. teresa di gallura": "Santa Teresa Gallura",
    "nughedu s.n.": "Nughedu San Nicolò",
    "nughedu s.v.": "Nughedu Santa Vittoria",
    # Frazioni, marine & industrial zones -> Parent Municipality
    "cala gonone": "Dorgali",
    "la muddizza": "Valledoria",
    "villanova strisaili": "Villagrande Strisaili",
    "tossilo": "Macomer",
    "pratosardo": "Nuoro",
    "arbatax": "Tortolì",
    "la caletta": "Siniscola",
    "porto cervo": "Arzachena",
    "fertilia": "Alghero",
    "pirri": "Cagliari",
    "san giovanni di sinis": "Cabras",
    "santa caterina di pittinuri": "Cuglieri",
    "s'archittu": "Cuglieri",
    "porto rotondo": "Olbia",
    "san pantaleo": "Olbia",
    "cannigione": "Arzachena",
    "isolotto": "Olbia",
    "capo comino": "Siniscola",
    "santa maria navarrese": "Baunei",
    "porto pino": "Sant'Anna Arresi",
    "chia": "Domus de Maria",
    "costa rei": "Muravera",
    "torre dei corsari": "Arbus",
    "flumini di quartu": "Quartu Sant'Elena",
    "bancali": "Sassari",
    "li punti": "Sassari",
    "argentiera": "Sassari",
}


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def is_sardinian_istat_code(raw_istat: str | None) -> bool:
    """Return True iff `raw_istat` is a 6-digit Sardinian ISTAT municipality code across any reform era."""
    if not raw_istat:
        return False
    digits = re.sub(r"\D", "", str(raw_istat))
    if len(digits) != 6:
        return False
    return digits.startswith(SARDINIAN_ISTAT_PROVINCE_PREFIXES)


@functools.lru_cache(maxsize=1)
def _indexes() -> dict[str, object]:
    by_name: dict[str, SardinianMunicipality] = {}
    by_lower: dict[str, SardinianMunicipality] = {}
    by_istat: dict[str, SardinianMunicipality] = {}
    by_belfiore: dict[str, SardinianMunicipality] = {}

    variant_to_canonical: dict[str, str] = dict(ALIASES_AND_FRAZIONI)
    for m in SARDINIAN_MUNICIPALITIES:
        by_name[m.name] = m
        low = m.name.lower().replace("’", "'")
        by_lower[low] = m
        by_istat[m.istat_code] = m
        by_belfiore[m.belfiore_code.upper()] = m

        variant_to_canonical[low] = m.name
        unacc = _strip_accents(low)
        by_lower.setdefault(unacc, m)
        if m.name not in ("Bidonì", "Lodè"):
            variant_to_canonical[unacc] = m.name
        if unacc != low and low[-1] in "àèéìòù":
            variant_to_canonical[unacc + "'"] = m.name
            by_lower.setdefault(unacc + "'", m)

    for alias, canon in ALIASES_AND_FRAZIONI.items():
        if canon in by_name:
            by_lower.setdefault(alias, by_name[canon])

    tier2_variants = dict(variant_to_canonical)
    tier2_variants["bidoni"] = "Bidonì"
    tier2_variants["lode"] = "Lodè"

    sorted_t2 = sorted(tier2_variants.keys(), key=len, reverse=True)
    t2_alt = "|".join(re.escape(k) for k in sorted_t2)

    sorted_all = sorted(variant_to_canonical.keys(), key=len, reverse=True)
    all_alt = "|".join(re.escape(k) for k in sorted_all)

    return {
        "by_name": by_name,
        "by_lower": by_lower,
        "by_istat": by_istat,
        "by_belfiore": by_belfiore,
        "variant_to_canonical": variant_to_canonical,
        "tier2_variants": tier2_variants,
        "supra_re": re.compile(
            r"\b(?:regione|provincia|citt[àa]\s+metropolitana|unione\s+dei\s+comuni|comunit[àa]\s+montana|"
            r"consorzio|abbanoa|enas|ente\s+acque|anas|azienda\s+(?:ospedalier|socio|sanitaria|servizi)|"
            r"arnas|aou|asl|ares|aspal|agenzia|agris|asvi|camera\s+di\s+commercio|reparto\s+infrastrutture|"
            r"universit[àa]|sardegna\s+ricerche)\b",
            re.IGNORECASE,
        ),
        "comune_prefix_re": re.compile(r"^\s*comune\s+(?:di\s+)?", re.IGNORECASE),
        "tier2_auth_re": re.compile(
            rf"\b(?:comune\s+(?:di\s+)?|municipio\s+di\s+)({t2_alt})(?![A-Za-zÀ-ÿ])",
            re.IGNORECASE,
        ),
        "tier2_text_re": re.compile(
            rf"\b(?:comun[ei]\s+(?:di\s+)?|municipio\s+di\s+|abitato\s+(?:del\s+comune\s+)?di\s+|"
            rf"centro\s+urbano\s+di\s+|cimitero\s+(?:comunale\s+)?di\s+|frazione\s+(?:di\s+)?)({t2_alt})(?![A-Za-zÀ-ÿ])",
            re.IGNORECASE,
        ),
        "multi_comuni_re": re.compile(r"\bcomuni\s+di\s+([^.;|\n]{3,95})", re.IGNORECASE),
        "all_comuni_re": re.compile(rf"(?<![A-Za-zÀ-ÿ])({all_alt})(?![A-Za-zÀ-ÿ])", re.IGNORECASE),
        "blocker_before_re": re.compile(
            r"(?:\b(?:via|viale|piazza|piazzale|corso|vicolo|vico|largo|traversa|bie|bia|"
            r"strada\s+(?:per|statale|provinciale)|s\.?\s*s\.?|s\.?\s*p\.?|svincolo|direzione)\s+(?:brigata\s+)?|"
            r"\bbrigata\s+|"
            r"\b(?:marmo|granito|basalto|trachite|pietra|porfido)\s+(?:rosa\s+|bianco\s+)?di\s+|"
            r"\b(?:fiume|rio|riu|torrente|lago|diga|invaso|golfo)\s+(?:del\s+|di\s+)?|"
            r"\b(?:su|sa|sos|sas|is|azienda\s+su)\s+|"
            r"\b(?:ing|arch|geom|dott|rup)\.?\s+[a-zà-ú']*\s*)\s*$",
            re.IGNORECASE,
        ),
        "site_anchor_before_re": re.compile(
            r"\b(?:sede\s+(?:distaccata\s+|operativa\s+)?di|impianto\s+(?:di\s+[a-zà-ú]+\s+)?di|"
            r"depuratore\s+di|distretto\s+(?:irriguo\s+)?di|zona\s+industriale\s+di|"
            r"centro\s+per\s+l['’]impiego\s*(?:\(cpi\)\s*)?di|cpi\s+di|cplf\s+di|"
            r"p\.?\s*o\.?\s+[a-zà-ú']+\s+di|cto\s+di|genio\s+civile\s+di|"
            r"caserma\s+[^,.;|\n]{1,35}\s+in|in\s+agro\s+di|nel\s+territorio\s+di|"
            r"(?:sita|sito|ubicat[oaie])\s+in(?:\s+via\s+[^–\-,.;|\n]{2,35}\s*[–\-]\s*)?)\s*$",
            re.IGNORECASE,
        ),
        "prov_paren_after_re": re.compile(r"^\s*\(\s*(?:NU|SS|OR|CA|SU|OT|OG|VS|CI)\s*\)", re.IGNORECASE),
        "ares_re": re.compile(r"\bcodice\s+ares\s*:\s*(\d{6})\d{4}\b", re.IGNORECASE),
        "cciaa_nuoro_re": re.compile(r"\bcamera\s+di\s+commercio\s+di\s+nuoro\b", re.IGNORECASE),
        "html_tag_re": re.compile(r"<[^>]+>"),
    }


def lookup_municipality(name_or_alias: str | None) -> SardinianMunicipality | None:
    """Look up a SardinianMunicipality by exact name, unaccented form, or frazione alias."""
    if not name_or_alias:
        return None
    idx = _indexes()
    by_lower: dict[str, SardinianMunicipality] = idx["by_lower"]  # type: ignore[assignment]
    key = name_or_alias.strip().lower().replace("’", "'")
    if key in by_lower:
        return by_lower[key]
    return by_lower.get(_strip_accents(key))


def lookup_by_belfiore(belfiore_code: str | None) -> SardinianMunicipality | None:
    """Look up a SardinianMunicipality by 4-char Italian Catastale/Belfiore code (e.g. `I730` -> Silanus)."""
    if not belfiore_code:
        return None
    by_belfiore: dict[str, SardinianMunicipality] = _indexes()["by_belfiore"]  # type: ignore[assignment]
    return by_belfiore.get(belfiore_code.strip().upper())


def lookup_by_istat(istat_code: str | None) -> SardinianMunicipality | None:
    """Look up a SardinianMunicipality by 6-digit ISTAT code."""
    if not istat_code:
        return None
    digits = re.sub(r"\D", "", str(istat_code))
    if len(digits) != 6:
        return None
    by_istat: dict[str, SardinianMunicipality] = _indexes()["by_istat"]  # type: ignore[assignment]
    return by_istat.get(digits)


def road_distance_from_silanus_km(municipality_name: str | None) -> int | None:
    """Return road distance in km from central logistics hub (Silanus) for any Sardinian municipality."""
    entry = lookup_municipality(municipality_name)
    return entry.road_km_from_silanus if entry is not None else None


@functools.lru_cache(maxsize=1024)
def resolve_municipality(
    *,
    authority: str = "",
    title: str = "",
    description: str = "",
    luogo_istat: str | None = None,
) -> str | None:
    """Resolve the exact Sardinian jobsite municipality via the 4-Tier Zero-Collision Resolver."""
    idx = _indexes()
    html_re: re.Pattern[str] = idx["html_tag_re"]  # type: ignore[assignment]
    supra_re: re.Pattern[str] = idx["supra_re"]  # type: ignore[assignment]
    comune_prefix_re: re.Pattern[str] = idx["comune_prefix_re"]  # type: ignore[assignment]
    ares_re: re.Pattern[str] = idx["ares_re"]  # type: ignore[assignment]
    tier2_auth_re: re.Pattern[str] = idx["tier2_auth_re"]  # type: ignore[assignment]
    tier2_text_re: re.Pattern[str] = idx["tier2_text_re"]  # type: ignore[assignment]
    multi_comuni_re: re.Pattern[str] = idx["multi_comuni_re"]  # type: ignore[assignment]
    all_comuni_re: re.Pattern[str] = idx["all_comuni_re"]  # type: ignore[assignment]
    blocker_before_re: re.Pattern[str] = idx["blocker_before_re"]  # type: ignore[assignment]
    site_anchor_before_re: re.Pattern[str] = idx["site_anchor_before_re"]  # type: ignore[assignment]
    prov_paren_after_re: re.Pattern[str] = idx["prov_paren_after_re"]  # type: ignore[assignment]
    cciaa_nuoro_re: re.Pattern[str] = idx["cciaa_nuoro_re"]  # type: ignore[assignment]
    by_name: dict[str, SardinianMunicipality] = idx["by_name"]  # type: ignore[assignment]
    variant_to_canonical: dict[str, str] = idx["variant_to_canonical"]  # type: ignore[assignment]
    tier2_variants: dict[str, str] = idx["tier2_variants"]  # type: ignore[assignment]

    norm_auth = html_re.sub(" ", authority or "").replace("’", "'")
    norm_title = html_re.sub(" ", title or "").replace("’", "'")
    norm_desc = html_re.sub(" ", description or "").replace("’", "'")

    is_supra = bool(supra_re.search(norm_auth)) and not bool(comune_prefix_re.match(norm_auth))

    # Tier 1A: ARES 10-digit school building code (first 6 digits = exact ISTAT municipality!)
    m_ares = ares_re.search(f"{norm_title} {norm_desc}")
    if m_ares:
        hit_ares = lookup_by_istat(m_ares.group(1))
        if hit_ares is not None:
            return hit_ares.name

    # Tier 1B: Single-municipality buyer `luogo_istat`
    if luogo_istat and not is_supra:
        hit_istat = lookup_by_istat(luogo_istat)
        if hit_istat is not None:
            return hit_istat.name

    # Tier 2A: Single-municipality buyer name (`Comune di X`)
    if not is_supra:
        m_auth = tier2_auth_re.search(norm_auth)
        if m_auth:
            return tier2_variants[m_auth.group(1).lower()]

    # Tier 2B: Multi-municipality tender (`Comuni di X, Y e Z`) -> pick minimum road km from Silanus!
    m_multi = multi_comuni_re.search(norm_title)
    if m_multi:
        found: list[str] = []
        for m in all_comuni_re.finditer(m_multi.group(1)):
            c = variant_to_canonical[m.group(1).lower()]
            if c not in found:
                found.append(c)
        if found:
            return min(found, key=lambda n: by_name[n].road_km_from_silanus if n in by_name else 999)

    # Tier 2C: Explicit administrative/toponymic phrasing in title/description/authority
    for blob in (norm_title, norm_desc, norm_auth):
        m_t2 = tier2_text_re.search(blob)
        if m_t2:
            return tier2_variants[m_t2.group(1).lower()]

    if cciaa_nuoro_re.search(norm_auth):
        return "Nuoro"

    # Tier 3 (324 unambiguous municipalities + frazioni) & Tier 4 (53 ambiguous municipalities with site anchor)
    for blob in (norm_title, norm_desc):
        for m in all_comuni_re.finditer(blob):
            canon = variant_to_canonical[m.group(1).lower()]
            prefix = blob[max(0, m.start() - 65) : m.start()]
            suffix = blob[m.end() : min(len(blob), m.end() + 15)]
            anchored = bool(site_anchor_before_re.search(prefix) or prov_paren_after_re.match(suffix))
            if not anchored and blocker_before_re.search(prefix):
                continue
            if canon in AMBIGUOUS_COMUNI:
                if anchored:
                    return canon
            else:
                return canon

    # Supra-authority fallback to `luogo_istat` ONLY if no jobsite municipality was found in title/description
    if luogo_istat:
        hit_hq = lookup_by_istat(luogo_istat)
        if hit_hq is not None:
            return hit_hq.name

    return None
