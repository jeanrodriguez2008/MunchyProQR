import io
import os
import openpyxl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(
    prefix="/api/salidas",
    tags=["Salidas de Producción"]
)


@router.post("/registrar", response_model=schemas.SalidaResponse)
def registrar_salida_qr(
    salida_data: schemas.SalidaCreate,
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(auth.requiere_analista_o_coordinador)
):
    if salida_data.num_recibo and salida_data.num_recibo.strip() != "":
        num_ticket = salida_data.num_recibo.strip()
        ticket_existente = db.query(models.SalidaProduccion).filter(
            models.SalidaProduccion.num_recibo == num_ticket
        ).first()

        if ticket_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El número de ticket '{num_ticket}' ya fue registrado previamente."
            )

    try:
        nueva_salida = models.SalidaProduccion(
            codigo_qr=str(salida_data.codigo_qr),
            codigo_articulo=str(salida_data.codigo_articulo) if salida_data.codigo_articulo else None,
            descripcion=str(salida_data.descripcion),
            lote=str(salida_data.lote) if salida_data.lote else None,
            fecha_vencimiento=str(salida_data.fecha_vencimiento) if salida_data.fecha_vencimiento else None,
            cantidad=int(salida_data.cantidad) if salida_data.cantidad else 1,
            num_recibo=str(salida_data.num_recibo).strip() if salida_data.num_recibo else None,
            turno=str(salida_data.turno) if salida_data.turno else None,
            grupo=str(salida_data.grupo) if salida_data.grupo else None,
            fecha_recibo=str(salida_data.fecha_recibo) if salida_data.fecha_recibo else None,
            fecha_contabilizacion=str(salida_data.fecha_contabilizacion) if salida_data.fecha_contabilizacion else None,
            num_op=str(salida_data.num_op) if salida_data.num_op else None,
            usuario_id=usuario_actual.id
        )
        
        db.add(nueva_salida)
        db.commit()
        db.refresh(nueva_salida)
        return nueva_salida
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al guardar en BD: {str(e)}"
        )


@router.get("/", response_model=List[schemas.SalidaResponse])
def listar_salidas(
    fecha: Optional[date] = Query(None, description="Filtrar por fecha (YYYY-MM-DD)"),
    articulo: Optional[str] = Query(None, description="Filtrar por descripción"),
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(auth.requiere_analista_o_coordinador)
):
    query = db.query(models.SalidaProduccion)
    if fecha:
        query = query.filter(func.date(models.SalidaProduccion.fecha_hora) == fecha)
    if articulo:
        query = query.filter(models.SalidaProduccion.descripcion.ilike(f"%{articulo}%"))
        
    return query.order_by(models.SalidaProduccion.fecha_hora.desc()).all()


@router.delete("/{salida_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_salida(
    salida_id: int,
    db: Session = Depends(get_db),
    usuario_coordinador: models.Usuario = Depends(auth.requiere_coordinador)
):
    registro = db.query(models.SalidaProduccion).filter(models.SalidaProduccion.id == salida_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="El registro no existe")
        
    db.delete(registro)
    db.commit()
    return None


@router.get("/dashboard/kpis")
def obtener_kpis_dashboard(
    db: Session = Depends(get_db),
    usuario_coordinador: models.Usuario = Depends(auth.requiere_coordinador)
):
    hoy = date.today()
    total_hoy = db.query(func.sum(models.SalidaProduccion.cantidad))\
                  .filter(func.date(models.SalidaProduccion.fecha_hora) == hoy)\
                  .scalar() or 0

    totales_por_sku = db.query(
                          models.SalidaProduccion.codigo_articulo,
                          models.SalidaProduccion.descripcion,
                          func.sum(models.SalidaProduccion.cantidad).label("total")
                      )\
                      .filter(func.date(models.SalidaProduccion.fecha_hora) == hoy)\
                      .group_by(models.SalidaProduccion.codigo_articulo, models.SalidaProduccion.descripcion)\
                      .order_by(func.sum(models.SalidaProduccion.cantidad).desc())\
                      .all()

    totales_por_grupo = db.query(
                            models.SalidaProduccion.grupo,
                            func.sum(models.SalidaProduccion.cantidad).label("total")
                        )\
                        .filter(func.date(models.SalidaProduccion.fecha_hora) == hoy)\
                        .group_by(models.SalidaProduccion.grupo)\
                        .order_by(func.sum(models.SalidaProduccion.cantidad).desc())\
                        .all()

    return {
        "fecha": hoy.strftime("%d/%m/%Y"),
        "total_unidades_hoy": total_hoy,
        "totales_sku": [
            {
                "sku": item.codigo_articulo or "N/A",
                "descripcion": item.descripcion,
                "total": item.total
            } for item in totales_por_sku
        ],
        "totales_grupo": [
            {
                "grupo": item.grupo if item.grupo else "Sin Grupo",
                "total": item.total
            } for item in totales_por_grupo
        ]
    }


@router.get("/exportar-excel")
def exportar_excel(
    db: Session = Depends(get_db),
    usuario_coordinador: models.Usuario = Depends(auth.requiere_coordinador)
):
    salidas = db.query(models.SalidaProduccion).order_by(models.SalidaProduccion.fecha_hora.desc()).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Salidas QR Munchy"

    encabezados = [
        "ID", "Código del Artículo", "Descripción", "Lote", "Fecha de Vencimiento",
        "Cantidad (und)", "Número de Ticket (recibo)", "Turno", "Grupo",
        "Fecha de Recibo", "Unidad de Medida", "Número de OP",
        "Contenido QR Bruto", "Fecha/Hora Escaneo", "Usuario Escáner"
    ]
    ws.append(encabezados)

    for col in range(1, len(encabezados) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)

    for s in salidas:
        nombre_usuario = s.usuario.username if s.usuario else "Desconocido"
        ws.append([
            s.id,
            s.codigo_articulo or "N/A",
            s.descripcion,
            s.lote or "N/A",
            s.fecha_vencimiento or "N/A",
            s.cantidad,
            s.num_recibo or "N/A",
            s.turno or "N/A",
            s.grupo or "N/A",
            s.fecha_recibo or "N/A",
            s.fecha_contabilizacion or "UND",
            s.num_op or "N/A",
            s.codigo_qr,
            s.fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
            nombre_usuario
        ])

    nombre_archivo = f"Respaldo_Salidas_Munchy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(nombre_archivo)

    return FileResponse(
        path=nombre_archivo,
        filename=nombre_archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# --- REPORTE PDF CON LOGO, GRÁFICOS, RESUMEN DE PRODUCCIÓN Y TOTAL GENERAL ---
@router.get("/reporte-pdf")
def generar_reporte_pdf(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(auth.requiere_analista_o_coordinador)
):
    query = db.query(models.SalidaProduccion).filter(
        func.date(models.SalidaProduccion.fecha_hora) >= fecha_inicio,
        func.date(models.SalidaProduccion.fecha_hora) <= fecha_fin
    )
    salidas = query.all()

    if not salidas:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron registros de producción en el lapso seleccionado."
        )

    total_unidades = sum(s.cantidad for s in salidas)
    
    dict_sku = {}
    for s in salidas:
        key = (s.codigo_articulo or "N/A", s.descripcion)
        dict_sku[key] = dict_sku.get(key, 0) + s.cantidad

    dict_grupo_turno = {}
    for s in salidas:
        g = s.grupo or "Sin Grupo"
        t = s.turno or "Sin Turno"
        dict_grupo_turno[(g, t)] = dict_grupo_turno.get((g, t), 0) + s.cantidad

    sku_lider = max(dict_sku.items(), key=lambda x: x[1]) if dict_sku else (("N/A", "N/A"), 0)

    # 1. Gráficos en memoria
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    labels_sku = [k[0] for k in dict_sku.keys()]
    valores_sku = list(dict_sku.values())
    ax1.bar(labels_sku, valores_sku, color='#4F46E5')
    ax1.set_title('Unidades por SKU', fontsize=10, fontweight='bold')
    ax1.tick_params(axis='x', rotation=45, labelsize=8)

    labels_gt = [f"G:{k[0]}-T:{k[1]}" for k in dict_grupo_turno.keys()]
    valores_gt = list(dict_grupo_turno.values())
    ax2.bar(labels_gt, valores_gt, color='#10B981')
    ax2.set_title('Producción Grupo / Turno', fontsize=10, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45, labelsize=8)

    plt.tight_layout()
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=150)
    img_buf.seek(0)
    plt.close()

    # 2. Generar PDF
    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1E3A8A"), spaceAfter=6)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=9, textColor=colors.gray, spaceAfter=12)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=10)

    elementos = []

    # Insertar Logo en el PDF si existe
    ruta_logo = os.path.join("app", "static", "img", "logo.png")
    if os.path.exists(ruta_logo):
        elementos.append(Image(ruta_logo, width=120, height=45))
        elementos.append(Spacer(1, 8))

    elementos.append(Paragraph("<b>ALIMENTOS MUNCHY, C.A.</b>", title_style))
    elementos.append(Paragraph(f"<b>Informe de Producción</b> | Lapso: {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}", subtitle_style))
    elementos.append(Spacer(1, 10))

    resumen_texto = f"""
    Durante el periodo comprendido entre el <b>{fecha_inicio.strftime('%d/%m/%Y')}</b> y el <b>{fecha_fin.strftime('%d/%m/%Y')}</b>, 
    se registró un volumen total de producción de <b>{total_unidades:,.0f} unidades</b> (desglosadas en {len(salidas)} tickets escaneados). 
    El producto con mayor volumen registrado fue <b>{sku_lider[0][1]}</b> (Código: {sku_lider[0][0]}) acumulando un total de 
    <b>{sku_lider[1]:,.0f} unidades</b>.
    """.replace(',', '.')
    
    elementos.append(Paragraph("<b>RESUMEN DE PRODUCCION</b>", styles['Heading2']))
    elementos.append(Paragraph(resumen_texto, body_style))
    elementos.append(Spacer(1, 10))

    elementos.append(Image(img_buf, width=500, height=200))
    elementos.append(Spacer(1, 15))

    elementos.append(Paragraph("<b>DESGLOSE DE PRODUCCIÓN POR GRUPO, TURNO Y SKU</b>", styles['Heading3']))
    
    tabla_datos = [["Código SKU", "Descripción del Artículo", "Grupo", "Turno", "Cant. Total (und)"]]
    for (sku, desc), cant in dict_sku.items():
        ejemplo = next((s for s in salidas if (s.codigo_articulo or "N/A") == sku), None)
        grupo_str = ejemplo.grupo if ejemplo and ejemplo.grupo else "N/A"
        turno_str = ejemplo.turno if ejemplo and ejemplo.turno else "N/A"
        tabla_datos.append([sku, desc[:35], grupo_str, turno_str, f"{cant:,.0f}".replace(',', '.')])

    # Fila final con la sumatoria del Total General
    tabla_datos.append(["TOTAL GENERAL", "", "", "", f"{total_unidades:,.0f}".replace(',', '.')])

    t = Table(tabla_datos, colWidths=[80, 220, 60, 60, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor("#F9FAFB")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        
        # Estilos aplicados a la fila de TOTAL GENERAL
        ('SPAN', (0, -1), (3, -1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#10B981")),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, -1), (0, -1), 'LEFT'),
    ]))
    
    elementos.append(t)

    doc.build(elementos)
    pdf_buf.seek(0)

    nombre_pdf = f"Reporte_Produccion_Munchy_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={nombre_pdf}"}
    )