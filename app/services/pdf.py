from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

def render_invoice_pdf(*, business, invoice, items, party_name: str, title: str) -> bytes:
    buffer = BytesIO(); pdf = canvas.Canvas(buffer, pagesize=A4); width, height = A4
    pdf.setTitle(invoice.invoice_number); y = height - 22 * mm
    pdf.setFont("Helvetica-Bold", 18); pdf.drawString(18 * mm, y, business.business_name); y -= 8 * mm
    pdf.setFont("Helvetica", 9)
    for value in [business.address, business.phone, business.email]:
        if value: pdf.drawString(18 * mm, y, value); y -= 5 * mm
    y -= 6 * mm; pdf.setFont("Helvetica-Bold", 15); pdf.drawRightString(width - 18 * mm, y + 18 * mm, title)
    pdf.setFont("Helvetica", 10); pdf.drawRightString(width - 18 * mm, y + 10 * mm, f"No: {invoice.invoice_number}"); pdf.drawRightString(width - 18 * mm, y + 4 * mm, f"Date: {invoice.invoice_date.isoformat()}")
    y -= 7 * mm; pdf.setFont("Helvetica-Bold", 10); pdf.drawString(18 * mm, y, f"Party: {party_name}"); y -= 10 * mm
    headers = [(18, "Description"), (108, "Qty"), (130, "Price"), (158, "Tax"), (181, "Total")]
    pdf.setFont("Helvetica-Bold", 9)
    for x, text in headers: pdf.drawString(x * mm, y, text)
    y -= 5 * mm; pdf.line(18 * mm, y, width - 18 * mm, y); y -= 6 * mm; pdf.setFont("Helvetica", 9)
    for item in items:
        if y < 35 * mm: pdf.showPage(); y = height - 25 * mm
        pdf.drawString(18 * mm, y, item.description[:48]); pdf.drawRightString(123 * mm, y, str(item.quantity)); pdf.drawRightString(153 * mm, y, f"{item.unit_price:,.2f}"); pdf.drawRightString(177 * mm, y, f"{item.tax_amount:,.2f}"); pdf.drawRightString(205 * mm, y, f"{item.line_total:,.2f}"); y -= 6 * mm
    y -= 6 * mm; pdf.line(125 * mm, y, width - 18 * mm, y); y -= 6 * mm
    for label, amount in [("Subtotal", invoice.subtotal), ("Discount", invoice.discount_total), ("Tax", invoice.tax_total), ("Grand Total", invoice.grand_total), ("Paid", invoice.paid_amount), ("Due", invoice.due_amount)]:
        pdf.setFont("Helvetica-Bold" if label in {"Grand Total", "Due"} else "Helvetica", 10); pdf.drawRightString(170 * mm, y, label); pdf.drawRightString(205 * mm, y, f"PKR {amount:,.2f}"); y -= 6 * mm
    pdf.setFont("Helvetica", 8); pdf.drawString(18 * mm, 15 * mm, "Computer-generated invoice — Paint Shop ERP")
    pdf.save(); return buffer.getvalue()
