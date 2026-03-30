"""Tests para servico de ingestao XLSX (UPLD-02, UPLD-05, idempotencia)."""
import pytest


@pytest.mark.skip(reason="Wave 0 stub — implementar apos Task 2+3")
def test_ingestao_escreve_sqlite():
    """UPLD-02: Apos ingestao, linha inserida em consumo_mensal SQLite."""
    pass


@pytest.mark.skip(reason="Wave 0 stub — implementar apos Task 2+3")
def test_cpe_routing():
    """UPLD-05: CPE detectado do nome de ficheiro resolve location_id correcto."""
    pass


@pytest.mark.skip(reason="Wave 0 stub — implementar apos Task 2+3")
def test_idempotencia():
    """Segundo upload do mesmo XLSX nao duplica dados (INSERT OR IGNORE)."""
    pass


@pytest.mark.skip(reason="Wave 0 stub — implementar apos Task 2+3")
def test_cpe_nao_detectado():
    """Upload com ficheiro sem CPE no nome retorna erro util."""
    pass
