from __future__ import annotations

import io
from pathlib import Path
import zipfile
import pytest

from sardegna_radar.cme.parser import CMEParser
from sardegna_radar.models import CAVProductCategory, ProductLine

BOLOTANA_CME_PDF = Path(
    r"C:\Users\Massimiliano\Desktop\PROGETTO_ESECUTIVO\PROGETTO_ESECUTIVO_pdf"
    r"\PE_All.B_Computo metrico-quadro economico_signed.pdf"
)
SAMPLE_CME_PDF = Path(__file__).parent / "fixtures" / "sample_cme.pdf"


class TestPortableSampleCMEFixture:
    def test_sample_cme_fixture_matches_linea_a_b_3decimal_and_excludes_s4_and_basalt(self) -> None:
        parser = CMEParser()
        result = parser.parse_path(SAMPLE_CME_PDF)
        assert result.total_raw_items == 4
        by_num = {it.item_number: it for it in result.matched_items}
        assert 1 in by_num and by_num[1].quantity == pytest.approx(8.0)
        assert by_num[1].product_line == ProductLine.LINEA_A
        assert 2 in by_num and by_num[2].quantity == pytest.approx(0.45)
        assert by_num[2].product_line == ProductLine.LINEA_B
        # Item 3 (S4 ready-mix concrete + B450C) and Item 4 (basalt kerb) MUST be discarded
        assert 3 not in by_num
        assert 4 not in by_num


@pytest.mark.skipif(not BOLOTANA_CME_PDF.exists(), reason="Bolotana ground-truth PDF not present on disk")
class TestBolotanaRealCMEParser:
    def test_extracts_exact_edilmorittu_items_and_rejects_stone_and_readymix(self) -> None:
        parser = CMEParser()
        result = parser.parse_path(BOLOTANA_CME_PDF)

        # Ground truth: Bolotana CME has 43 total items
        assert result.total_raw_items == 43

        by_num = {item.item_number: item for item in result.matched_items}

        # --- MUST EXTRACT (Linea A + Linea B) ---
        # Item 12: 8 pz pozzetti cls vibrocompresso 50x50 con griglia ghisa (Linea A)
        assert 12 in by_num
        assert by_num[12].quantity == pytest.approx(8.0)
        assert by_num[12].product_line == ProductLine.LINEA_A
        assert by_num[12].category == CAVProductCategory.MANHOLES_CHAMBERS
        assert "SAR26_PF.0003.0015.0002" in by_num[12].tariff_code

        # Item 9: 76,50 m³ ghiaia (Linea B)
        assert 9 in by_num
        assert by_num[9].quantity == pytest.approx(76.50)
        assert by_num[9].product_line == ProductLine.LINEA_B
        assert by_num[9].category == CAVProductCategory.AGGREGATES_INERTI

        # Item 11: 2.981,89 kg rete elettrosaldata B450C Ø10 20x20 (Linea B - PriMus acute accent!)
        assert 11 in by_num
        assert by_num[11].quantity == pytest.approx(2981.89)
        assert by_num[11].total_price_eur == pytest.approx(5248.13)
        assert by_num[11].product_line == ProductLine.LINEA_B
        assert by_num[11].category == CAVProductCategory.STEEL_REBAR_MESH

        # Item 13: 50,00 m tubo fogna PVC SN4 Ø110 (Linea B)
        assert 13 in by_num
        assert by_num[13].quantity == pytest.approx(50.0)
        assert by_num[13].product_line == ProductLine.LINEA_B
        assert by_num[13].category == CAVProductCategory.PLUMBING_PVC_MULTILAYER

        # Item 14: 100,00 m tubo multistrato isolato Ø32 (Linea B)
        assert 14 in by_num
        assert by_num[14].quantity == pytest.approx(100.0)
        assert by_num[14].category == CAVProductCategory.PLUMBING_PVC_MULTILAYER

        # Item 23: 20,00 m² muratura in mattoni laterizi forati sp. 8 cm + malta R32.5 (Linea B)
        assert 23 in by_num
        assert by_num[23].quantity == pytest.approx(20.0)
        assert by_num[23].category == CAVProductCategory.BRICKS_MASONRY_BINDERS

        # Item 18 (spans across page break!): 83,39 m² risanamento calcestruzzo con malte tecniche
        assert 18 in by_num
        assert by_num[18].quantity == pytest.approx(83.39)
        assert by_num[18].category == CAVProductCategory.BRICKS_MASONRY_BINDERS

        # Items 20 & 32: Guaine impermeabilizzanti (16,32 m² liquida + 338,57 m² bituminosa)
        assert 20 in by_num and by_num[20].quantity == pytest.approx(16.32)
        assert 32 in by_num and by_num[32].quantity == pytest.approx(338.57)
        assert by_num[32].category == CAVProductCategory.WATERPROOFING_PAINTS

        # Item 26: 148,00 m² rasatura con malta premiscelata
        assert 26 in by_num and by_num[26].quantity == pytest.approx(148.0)

        # --- MUST STRICTLY DISCARD (Hard Exclusions) ---
        forbidden_items = {
            10,  # 51,32 m³ Calcestruzzo C12/15 classe S4 autobetoniera (> 1 t)
            33,  # 295,00 m² Piastrelle di basalto
            34,  # 75,00 m² Lastre di marmo bianco di Orosei
            35,  # 108,20 m Cordonata stradale in materiale lapideo (basalto)
            36,  # 101,85 m² Cubetti in basalto su massetto in cls
            37,  # 101,70 m² Rivestimento pareti in lastre di basalto
            38,  # 5,10 m² Rivestimento pareti in lastre di travertino
            1, 2, 3, 4, 5, 6, 7, 8,  # Demolizioni cordonate/pavimenti, rimozioni, scavi
            21, 22, 27, 39, 40, 41, 42, 43,  # Spicconature, raschiature, trasporto/conferimento discarica
        }
        leaked = forbidden_items.intersection(by_num.keys())
        assert leaked == set(), f"Forbidden items leaked into matched catalog: {leaked}"

    def test_streaming_zip_extracts_only_cme_and_strips_p7m_envelope(self) -> None:
        raw_pdf = BOLOTANA_CME_PDF.read_bytes()
        # Simulate PKCS#7 (.pdf.p7m) DER envelope wrapping the PDF bytes
        fake_p7m_bytes = b"\x30\x82\x99\x99\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x02" + raw_pdf + b"\x00\x00\x30\x80"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("PE_Tavola_01_Inquadramento.pdf", b"%PDF-1.4 FAKE DRAWING DO NOT PARSE")
            zf.writestr("PE_All.A_Relazione_Tecnica_Illustrativa.pdf", b"%PDF-1.4 FAKE REPORT")
            zf.writestr("PE_All.B_Computo_Metrico_Estimativo.pdf.p7m", fake_p7m_bytes)

        parser = CMEParser()
        result = parser.parse_bytes(buf.getvalue(), filename="AllegatiProgetto.zip")

        assert "Computo_Metrico_Estimativo" in result.selected_filename
        assert result.total_raw_items == 43
        by_num = {item.item_number: item for item in result.matched_items}
        assert by_num[12].quantity == pytest.approx(8.0)
        assert by_num[11].quantity == pytest.approx(2981.89)
        assert 35 not in by_num
        assert 10 not in by_num
