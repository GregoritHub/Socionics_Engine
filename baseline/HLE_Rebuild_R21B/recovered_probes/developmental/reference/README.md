# Preserved source material

The originals are unchanged. `Source_Manifest.json` maps their original filenames to packaged paths and SHA-256 hashes. The foundation and roadmap are historical preparation snapshots; current progress is in `docs/Progress_After_R5.md`.

The additional Crux v6 document supplies the complete route-name table and the explicit claim grades. All other supplied originals remain present, including the unchanged 5.2.1 archive. They are reference data, never runtime imports.

DOCX text extracts use `Pxxxx` locators counting every Word paragraph under the document body, including table and empty paragraphs. `tools/extract_docx.py` reproduces those locators. Math text is retained in document order; text extraction does not preserve every visual equation layout. Use the original document when typography matters. The Canon text was extracted using `pdftotext -layout`; its page numbers refer to the PDF.
