import sys
import os
import math
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, QPen,
    QBrush, QPainterPath, QPixmap
)
from PyQt6.QtCore import Qt, QPointF

app = QApplication(sys.argv)

def render_spider(phase=0.0, is_walking=False, size=96):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx = size / 2.0
    cy = size / 2.0

    painter.translate(cx, cy)

    # NO SHADOW! (Removed completely as requested)

    # Leg configurations matching the anatomical blueprint & silhouette concepts:
    # 4 pairs originating from Cephalothorax (prosoma center: y = -3)
    # Each leg defined by:
    # side: -1 (left), +1 (right)
    # att_pt: (att_x, att_y) on cephalothorax rim
    # Joint 1 (Coxa/Femur knee): (k1_x, k1_y)
    # Joint 2 (Tibia knee): (k2_x, k2_y)
    # Joint 3 (Tarsus claw tip): (tip_x, tip_y)
    # gait_grp: 0 or 1 for alternating gait

    # Base resting leg coordinates relative to spider center (0,0):
    leg_templates = [
        # Pair 1: Front reaching high & inward (like blueprint Leg 1)
        {
            'side': -1,
            'att': (-4.5, -7.0),
            'knee1': (-12.0, -18.0),
            'knee2': (-13.0, -29.0),
            'tip': (-6.5, -38.0),
            'gait_grp': 0
        },
        # Pair 2: Front-lateral reaching out & forward (Leg 2)
        {
            'side': -1,
            'att': (-6.5, -4.5),
            'knee1': (-18.0, -12.0),
            'knee2': (-26.0, -16.0),
            'tip': (-24.0, -3.0),
            'gait_grp': 1
        },
        # Pair 3: Lateral-rear reaching out & backward (Leg 3)
        {
            'side': -1,
            'att': (-6.8, -1.0),
            'knee1': (-19.0, 3.0),
            'knee2': (-27.0, 10.0),
            'tip': (-21.0, 24.0),
            'gait_grp': 0
        },
        # Pair 4: Rear reaching far back & curving in (Leg 4)
        {
            'side': -1,
            'att': (-5.0, 2.5),
            'knee1': (-14.0, 13.0),
            'knee2': (-17.0, 27.0),
            'tip': (-7.5, 38.0),
            'gait_grp': 1
        },
    ]

    # Generate right side symmetrically
    all_legs = []
    for l in leg_templates:
        all_legs.append(l) # Left
        r = {
            'side': 1,
            'att': (-l['att'][0], l['att'][1]),
            'knee1': (-l['knee1'][0], l['knee1'][1]),
            'knee2': (-l['knee2'][0], l['knee2'][1]),
            'tip': (-l['tip'][0], l['tip'][1]),
            'gait_grp': 1 - l['gait_grp']
        }
        all_legs.append(r)

    # Chitin colors (sleek dark obsidian with elegant blue-indigo sheen)
    chitin_base = QColor(16, 18, 28)
    chitin_highlight = QColor(36, 42, 68)
    chitin_tip = QColor(50, 60, 95)

    # 1. DRAW 8 ARTICULATED LEGS
    for leg in all_legs:
        side = leg['side']
        att_x, att_y = leg['att']
        k1_x, k1_y = leg['knee1']
        k2_x, k2_y = leg['knee2']
        tip_x, tip_y = leg['tip']

        # Gait offsets
        if is_walking:
            phase_offset = 0.0 if leg['gait_grp'] == 0 else math.pi
            swing = math.sin(phase + phase_offset)
            lift = max(0.0, math.sin(phase + phase_offset))

            # Forward/back swing
            swing_dx = -side * swing * 3.5
            swing_dy = -swing * 4.0

            # Knee lift
            lift_dy = -lift * 4.0
            lift_dx = side * lift * 2.0

            k1_x += lift_dx * 0.5
            k1_y += lift_dy * 0.5
            k2_x += lift_dx + swing_dx * 0.5
            k2_y += lift_dy + swing_dy * 0.5
            tip_x += swing_dx
            tip_y += swing_dy
        else:
            # Subtle breathing idle micro-shift
            idle_shift = math.sin(phase * 0.7 + att_y) * 0.8
            tip_x += side * idle_shift * 0.3
            tip_y += idle_shift * 0.5

        # Draw smooth tapered chitin leg path using quadratic Bezier curves
        # Segment 1: Coxa -> Knee 1 (Femur)
        p1 = QPainterPath()
        p1.moveTo(att_x, att_y)
        p1.quadTo((att_x + k1_x) / 2.0 + side * 1.5, (att_y + k1_y) / 2.0, k1_x, k1_y)
        pen1 = QPen(chitin_base, 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen1)
        painter.drawPath(p1)

        # Subtle highlight along femur
        pen1_h = QPen(chitin_highlight, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen1_h)
        painter.drawPath(p1)

        # Segment 2: Knee 1 -> Knee 2 (Tibia)
        p2 = QPainterPath()
        p2.moveTo(k1_x, k1_y)
        p2.quadTo((k1_x + k2_x) / 2.0 + side * 1.0, (k1_y + k2_y) / 2.0, k2_x, k2_y)
        pen2 = QPen(chitin_base, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen2)
        painter.drawPath(p2)

        pen2_h = QPen(chitin_highlight, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen2_h)
        painter.drawPath(p2)

        # Segment 3: Knee 2 -> Claw Tip (Tarsus - tapering down to sharp claw)
        p3 = QPainterPath()
        p3.moveTo(k2_x, k2_y)
        p3.quadTo((k2_x + tip_x) / 2.0, (k2_y + tip_y) / 2.0, tip_x, tip_y)
        pen3 = QPen(chitin_base, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen3)
        painter.drawPath(p3)

        pen3_tip = QPen(chitin_tip, 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen3_tip)
        painter.drawPath(p3)

    # 2. DRAW ABDOMEN (Opisthosoma) - Behind cephalothorax
    ab_y = 12.0
    ab_rx = 11.5
    ab_ry = 14.5 + math.sin(phase * 0.6) * 0.4 # subtle breathing

    ab_path = QPainterPath()
    ab_path.addEllipse(QPointF(0, ab_y), ab_rx, ab_ry)

    ab_grad = QRadialGradient(-2.5, ab_y - 4.0, 16.0)
    ab_grad.setColorAt(0.0, QColor(36, 42, 68))     # Deep navy-indigo highlight
    ab_grad.setColorAt(0.55, QColor(18, 22, 36))    # Sleek dark chitin
    ab_grad.setColorAt(1.0, QColor(9, 11, 18))      # Near obsidian rim

    painter.setPen(QPen(QColor(99, 102, 241, 110), 1.2)) # Subtle sleek indigo rim
    painter.setBrush(ab_grad)
    painter.drawPath(ab_path)

    # Subtle dorsal specular gleam on abdomen (gives 3D curvature)
    gleam_path = QPainterPath()
    gleam_path.addEllipse(QPointF(-2.0, ab_y - 5.0), 4.5, 6.0)
    gleam_grad = QRadialGradient(-2.0, ab_y - 5.0, 6.0)
    gleam_grad.setColorAt(0.0, QColor(129, 140, 248, 50))
    gleam_grad.setColorAt(1.0, QColor(129, 140, 248, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gleam_grad)
    painter.drawPath(gleam_path)

    # 3. DRAW CEPHALOTHORAX (Prosoma / Head-Chest Hub)
    ceph_y = -3.0
    ceph_rx = 8.5
    ceph_ry = 8.0

    ceph_path = QPainterPath()
    ceph_path.addEllipse(QPointF(0, ceph_y), ceph_rx, ceph_ry)

    ceph_grad = QRadialGradient(-1.5, ceph_y - 2.5, 11.0)
    ceph_grad.setColorAt(0.0, QColor(42, 50, 80))
    ceph_grad.setColorAt(0.65, QColor(20, 24, 38))
    ceph_grad.setColorAt(1.0, QColor(10, 12, 20))

    painter.setPen(QPen(QColor(99, 102, 241, 130), 1.2))
    painter.setBrush(ceph_grad)
    painter.drawPath(ceph_path)

    # Pedipalps (front feelers/arms reaching forward)
    pp_anim = math.sin(phase * 1.5) * 2.0 if is_walking else math.sin(phase * 0.8) * 1.2
    painter.setPen(QPen(chitin_base, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(-2.5, -8.0), QPointF(-4.5, -13.0 + pp_anim))
    painter.drawLine(QPointF(-4.5, -13.0 + pp_anim), QPointF(-3.0, -16.0 + pp_anim))
    painter.drawLine(QPointF(2.5, -8.0), QPointF(4.5, -13.0 - pp_anim))
    painter.drawLine(QPointF(4.5, -13.0 - pp_anim), QPointF(3.0, -16.0 - pp_anim))

    # 4. CUTE JUMPING SPIDER EYES
    # Pair 1: Primary Large Center Eyes (Electric Blue/Cyan with shiny reflection)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(56, 189, 248)) # Vivid Cyan
    painter.drawEllipse(QPointF(-2.5, -6.8), 2.2, 2.2)
    painter.drawEllipse(QPointF(2.5, -6.8), 2.2, 2.2)

    # Large eye shiny specular catchlight (makes them look adorable & alive)
    painter.setBrush(QColor(255, 255, 255, 240))
    painter.drawEllipse(QPointF(-1.8, -7.4), 0.8, 0.8)
    painter.drawEllipse(QPointF(3.2, -7.4), 0.8, 0.8)

    # Pair 2: Lateral Secondary Eyes (Small soft glowing dots)
    painter.setBrush(QColor(165, 180, 252, 200)) # Lavender
    painter.drawEllipse(QPointF(-5.5, -5.5), 1.2, 1.2)
    painter.drawEllipse(QPointF(5.5, -5.5), 1.2, 1.2)

    painter.end()
    return pix

# Render idle and walking previews
p_idle = render_spider(phase=0.0, is_walking=False)
p_idle.save("scratch/spider_preview_idle.png", "PNG")

p_walk = render_spider(phase=math.pi / 2, is_walking=True)
p_walk.save("scratch/spider_preview_walk.png", "PNG")

print("Rendered scratch/spider_preview_idle.png and scratch/spider_preview_walk.png successfully!")
