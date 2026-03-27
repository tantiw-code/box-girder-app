"""
CALCULATION SHEET FOR BOX UP SINGLE GIRDER
สูตรตรงกับ Excel Single_girder.xlsx (For_European Hoist sheet)
เกณฑ์: Stress ≤ 1.6 T/cm² | L/(D1+D2+D3) ≥ 670
"""

import streamlit as st
import math

# ═══════════════════════════════════════════════════════════════════════════════
#  CORE CALCULATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_section(B, H, T1, T2, T3, T4,
                    Str=6.0, Cr=45.0, Wep=9.0, x=50.0, Rail=4):
    """
    คำนวณ Section Properties ของ Single Box Girder
    Input  : มิติทั้งหมดเป็น mm
    Output : dict (A=cm², Ix/Iy=cm⁴, ey/ex=mm, Wg=ton/m, ...)

    สูตรอ้างอิง: Excel For_European Hoist sheet
    ────────────────────────────────────────────────────────────────
    B    = ความกว้างหน้าตัด (Top flange)       T1 = ความหนา Web ซ้าย
    H    = ความสูง Web                         T2 = ความหนา Top Flange
    T3   = ความหนา Web ขวา                    T4 = ความหนา Bottom Flange
    B1   = ความกว้างภายใน = B-120-(T1+T3)
    Str  = ความหนา Stringer                    Cr = ความสูง Crane Rail
    Wep  = ความหนา Web plank                  x  = ความกว้าง Web plank
    Rail = จำนวน Rail
    ────────────────────────────────────────────────────────────────
    """
    # B1 ← Excel U23 = U11-120-(U15+U19)
    B1 = B - 120.0 - (T1 + T3)

    # Area [cm²] ← Excel AB11
    A = (B * T4 + B * T2 + 2.0 * H * T1) / 100.0

    # ex (horizontal centroid) [mm] ← Excel AB13
    ex = (B1 + T1 + T3) * 0.5

    # ey (vertical centroid from top) [mm] ← Excel AB15
    ey = (
        B  * T2 * 0.5 * T2 +
        B  * T4 * (T2 + H + 0.5 * T4) +
        2.0 * H * T1 * (0.5 * H + T2)
    ) / (A * 100.0)

    # Ix [cm⁴] ← Excel AB17 (ใช้ A แทน AB11 ตาม Excel ต้นฉบับ)
    Ix = (
        (B * T2**3 / 12.0) + B * T2 * (ey - T2 / 2.0)**2 +
        (A * T4**3 / 12.0) + B * T4 * (T2 + H + 0.5 * T4 - ey)**2 +
        2.0 * ((T1 * H**3 / 12.0) + T1 * H * (0.5 * H + T2 - ey)**2)
    ) / 1e4

    # Iy [cm⁴] ← Excel AB19
    Iy = (
        T4 * B**3 / 12.0 +
        T2 * B**3 / 12.0 +
        2.0 * (H * T1**3 / 12.0 + H * T1 * (0.5 * (B1 + T1))**2)
    ) / 1e4

    # Wg [ton/m] ← Excel AB21
    Wg = (
        (T4 * B) + (T2 * B) +
        (T1 * (H + Cr)) + (T3 * (H + Cr)) +
        (T1 * B1 * 0.8)
    ) * 8.1 / 1e6

    return dict(
        A=A, Wg=Wg, ey=ey, ex=ex, Ix=Ix, Iy=Iy,
        B1=B1,
        B=B, H=H, T1=T1, T2=T2, T3=T3, T4=T4,
        Str=Str, Cr=Cr, Wep=Wep, x=x, Rail=Rail,
        W_total=None,
    )


def compute_weight(sec, SPAN_m):
    """
    น้ำหนักรวม Single Girder [Ton] ← Excel AH25
    =(Wg*SPAN) + (Str*B1*(H-50)*8.1/1e6/1000)*(SPAN/1.2)
              + (Wep*x*(SPAN*1000)*Rail*8.1/1e6/1000) + 0.4
    """
    Wg, B1, H = sec['Wg'], sec['B1'], sec['H']
    Str, Wep, x, Rail = sec['Str'], sec['Wep'], sec['x'], sec['Rail']

    W = (
        Wg * SPAN_m +
        (Str * B1 * (H - 50) * 8.1 / 1e6 / 1000) * (SPAN_m / 1.2) +
        (Wep * x * (SPAN_m * 1000) * Rail * 8.1 / 1e6 / 1000) +
        0.4
    )
    sec['W_total'] = W
    return W


def compute_checks(sec, LOAD, SPAN_m, W_HOIST):
    """
    คำนวณ Moment / Stress / Deflection ของ Single Girder
    ตรวจสอบจาก Excel ทุกสูตร
    """
    E    = 2100.0
    L_cm = SPAN_m * 100.0

    Ix, Iy = sec['Ix'], sec['Iy']
    Wg     = sec['Wg']
    ey, ex = sec['ey'], sec['ex']
    T2     = sec['T2']
    H      = sec['H']
    F      = LOAD + W_HOIST    # Total force

    # ── Bending Moments ─────────────────────────────────────────────────────
    # Mx by load ← Excel I35: =1.4*(Wh+LOAD)*SPAN*100/4
    Mx_load   = 1.4 * F * SPAN_m * 100.0 / 4.0

    # Mx by weight ← Excel I39: =1.1*Wg*SPAN²*100/8
    Mx_weight = 1.1 * Wg * SPAN_m**2 * 100.0 / 8.0

    Mx = Mx_load + Mx_weight          # ← Excel I43
    My = 0.05 * Mx                    # ← Excel I47

    # ── STRESS POINT 1 (Top zone) ── Excel S35, S39, S47 ────────────────────
    # Sx = Mx*(H-ey)/Ix/10
    Sx1  = Mx * (H - ey) / Ix / 10.0

    # Sy = My*ex/Iy/10
    Sy1  = My * ex / Iy / 10.0

    # Seq1 = Sx + Sy   ← Excel S47
    Seq1 = Sx1 + Sy1

    # ── STRESS POINT 2 (Bottom + shear zone) ── Excel AB35, AB39, AB43, AB47
    # Sx = Mx*ey/Ix/10
    Sx2  = Mx * ey / Ix / 10.0

    # Sy = My*ex/Iy/10  (same axis)
    Sy2  = My * ex / Iy / 10.0

    # Sfx = 1.4*F/4/T2²*100  (local flange bending) ← Excel AB43
    Sfx  = 1.4 * F / 4.0 / (T2**2) * 100.0

    # Seq2 = Sx + Sy + 0.75*Sfx   ← Excel AB47
    Seq2 = Sx2 + Sy2 + 0.75 * Sfx

    # ── DEFLECTION ── Excel AH35, AH39, AH43 ────────────────────────────────
    # D1 by load ← =LOAD*L³/(48*E*Ix)
    D1 = LOAD * L_cm**3 / (48.0 * E * Ix)

    # D2 by hoist ← =Wh*L³/(48*E*Ix)
    D2 = W_HOIST * L_cm**3 / (48.0 * E * Ix)

    # D3 by self weight ← =5*Wg*SPAN*L³/(384*E*Ix)
    D3 = 5.0 * Wg * SPAN_m * L_cm**3 / (384.0 * E * Ix)

    D_total  = D1 + D2 + D3
    L_D1     = L_cm / D1        if D1      > 0 else 9999
    L_D1D2   = L_cm / (D1+D2)   if D1+D2   > 0 else 9999
    L_D1D2D3 = L_cm / D_total   if D_total > 0 else 9999

    IyIx_pct = Iy / Ix * 100.0

    return dict(
        Mx_load=Mx_load, Mx_weight=Mx_weight, Mx=Mx, My=My,
        Sx1=Sx1, Sy1=Sy1, Seq1=Seq1,
        Sx2=Sx2, Sy2=Sy2, Sfx=Sfx, Seq2=Seq2,
        D1=D1, D2=D2, D3=D3,
        L_D1=L_D1, L_D1D2=L_D1D2, L_D1D2D3=L_D1D2D3,
        IyIx_pct=IyIx_pct,
    )


def check_criteria(res):
    """
    เกณฑ์การออกแบบ Single Girder
    1. Seq1 (Point 1) ≤ 1.6 T/cm²
    2. Seq2 (Point 2) ≤ 1.6 T/cm²
    3. L/(D1+D2+D3) ≥ 670
    """
    ok_iy  = 11.0 <= res['IyIx_pct'] <= 13.0
    ok_str = res['Seq1'] <= 1.6 and res['Seq2'] <= 1.6
    ok_def = res['L_D1D2D3'] >= 670
    return ok_iy, ok_str, ok_def, (ok_iy and ok_str and ok_def)


def find_best(LOAD, SPAN_m, W_HOIST,
              Str=6.0, Cr=45.0, Wep=9.0, x=50.0, Rail=4,
              H_min=400, H_max=1800, B_min=200, B_max=800):
    """
    วนหาหน้าตัดที่ผ่านเงื่อนไขทั้งหมด (น้ำหนักเบาที่สุด)
    """
    T_list = [6, 8, 9, 10, 12, 14, 16, 19, 22, 25, 28, 32]

    best, best_wg = None, 1e9

    for H in range(int(H_min), int(H_max) + 1, 25):
        for B in range(int(B_min), int(B_max) + 1, 25):
            # B1 ต้องเป็นบวก
            if B - 120 - 24 <= 0:   # T1+T3 min = 12, but need positive B1
                continue
            if B > H * 0.80 or B < H * 0.15:
                continue
            for T2 in T_list:        # Top flange (มักหนาที่สุด)
                for T4 in T_list:    # Bottom flange
                    for Tw in [6, 8, 9, 10, 12, 14]:  # T1=T3 (webs)
                        try:
                            sec = compute_section(
                                B, H, Tw, T2, Tw, T4,
                                Str=Str, Cr=Cr, Wep=Wep, x=x, Rail=int(Rail)
                            )
                            if sec['B1'] <= 0:
                                continue
                            compute_weight(sec, SPAN_m)
                            res = compute_checks(sec, LOAD, SPAN_m, W_HOIST)
                            _, _, _, passed = check_criteria(res)
                            if passed and sec['Wg'] < best_wg:
                                best_wg = sec['Wg']
                                best = (sec, res)
                        except Exception:
                            continue
    return best


# ═══════════════════════════════════════════════════════════════════════════════
#  STREAMLIT UI
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Single Girder Designer",
    page_icon="🏗️",
    layout="wide",
)

st.title("🏗️ CALCULATION SHEET — BOX UP SINGLE GIRDER")
st.caption("สูตรตาม Excel Single_girder.xlsx | SS400 | E = 2,100 T/cm²  |  เกณฑ์: Stress ≤ 1.6 T/cm²  |  L/(D1+D2+D3) ≥ 670")

tab_manual, tab_auto = st.tabs(["📋 Manual Check", "🚀 Auto-Optimize"])

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📥 ข้อมูลโครงการ")
    LOAD    = st.number_input("Load (Ton)",              value=10.0, step=0.5,  min_value=1.0)
    SPAN_m  = st.number_input("Span (m)",                value=19.6, step=0.5,  min_value=1.0)
    W_HOIST = st.number_input("Weight of Hoist (Ton)",   value=0.7,  step=0.1,  min_value=0.1)

    st.divider()
    st.header("🔩 Walkway / Rail Parameters")
    Str_in  = st.number_input("Str – Stringer thickness (mm)", value=6.0,  step=1.0)
    Cr_in   = st.number_input("Cr – Crane rail height (mm)",   value=45.0, step=5.0)
    Wep_in  = st.number_input("Wep – Web plank thickness (mm)",value=9.0,  step=1.0)
    x_in    = st.number_input("x – Web plank width (mm)",      value=50.0, step=5.0)
    Rail_in = st.number_input("Rail – จำนวน (ea)",             value=4,    step=1, min_value=1)


# ─── Helper: display results ─────────────────────────────────────────────────
def show_results(sec, res):
    ok_iy, ok_str, ok_def, passed = check_criteria(res)

    color = "#1a7f37" if passed else "#cf222e"
    label = "✅  PASS — ผ่านทุกเกณฑ์" if passed else "❌  FAIL — ไม่ผ่านบางเกณฑ์"
    st.markdown(
        f"<div style='background:{color};color:white;padding:10px 18px;"
        f"border-radius:6px;font-size:1.1rem;font-weight:600'>{label}</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    # ── KPI row
    k1, k2, k3 = st.columns(3)
    k1.metric("Max Stress (Point 1 & 2)",
              f"{max(res['Seq1'], res['Seq2']):.3f}  T/cm²",
              delta="เกณฑ์ ≤ 1.6 T/cm²",
              delta_color="normal" if ok_str else "inverse")
    k2.metric("L / (D1+D2+D3)",
              f"{res['L_D1D2D3']:.0f}",
              delta="เกณฑ์ ≥ 670",
              delta_color="normal" if ok_def else "inverse")
    k3.metric("Iy / Ix",
              f"{res['IyIx_pct']:.2f} %",
              delta="เกณฑ์ 11–13 %",
              delta_color="normal" if ok_iy else "inverse")

    # ── Weight
    W = sec.get('W_total')
    if W is not None:
        st.markdown(
            f"<div style='background:var(--color-background-secondary);"
            f"border:1.5px solid var(--color-border-primary);border-radius:8px;"
            f"padding:12px 22px;margin:10px 0;display:flex;align-items:center;gap:20px'>"
            f"<span style='font-size:14px;color:var(--color-text-secondary)'>⚖️  น้ำหนักรวม Single Girder</span>"
            f"<span style='font-size:1.5rem;font-weight:500;color:var(--color-text-primary)'>{W:.3f}  Tons</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Section | Properties | Moment
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("#### 📏 ขนาดหน้าตัด (mm)")
        st.table({
            "พารามิเตอร์": ["B (Top flange width)", "H (Web height)",
                             "T1 (Web ซ้าย)", "T2 (Top flange)",
                             "T3 (Web ขวา)", "T4 (Bottom flange)", "B1 (ภายใน)"],
            "ค่า": [f"{sec['B']:.0f}", f"{sec['H']:.0f}",
                    f"{sec['T1']:.0f}", f"{sec['T2']:.0f}",
                    f"{sec['T3']:.0f}", f"{sec['T4']:.0f}", f"{sec['B1']:.0f}"],
        })

    with c2:
        st.markdown("#### 📊 Section Properties")
        st.table({
            "สัญลักษณ์": ["A (cm²)", "Ix (cm⁴)", "Iy (cm⁴)",
                           "ey (mm)", "ex (mm)", "Iy/Ix (%)", "Wg (kg/m)"],
            "ค่า": [f"{sec['A']:.2f}", f"{sec['Ix']:,.2f}", f"{sec['Iy']:,.2f}",
                    f"{sec['ey']:.2f}", f"{sec['ex']:.2f}",
                    f"{res['IyIx_pct']:.2f}", f"{sec['Wg']*1000:.2f}"],
        })

    with c3:
        st.markdown("#### 🔩 Bending Moment (Ton-cm)")
        st.table({
            "รายการ": ["Mx by load", "Mx by weight", "Mx total", "My (0.05×Mx)"],
            "ค่า": [f"{res['Mx_load']:.2f}", f"{res['Mx_weight']:.2f}",
                    f"{res['Mx']:.2f}", f"{res['My']:.2f}"],
        })

    st.divider()

    # ── Stress + Deflection
    d1, d2 = st.columns(2)

    with d1:
        p1 = "✅" if res['Seq1'] <= 1.6 else "❌"
        p2 = "✅" if res['Seq2'] <= 1.6 else "❌"

        st.markdown(f"#### STRESS — POINT 1 (Top zone) {p1}")
        st.table({
            "": ["Sx  =  Mx×(H−ey)/Ix/10",
                 "Sy  =  My×ex/Iy/10",
                 "**Seq = Sx + Sy**"],
            "T/cm²": [f"{res['Sx1']:.4f}",
                      f"{res['Sy1']:.4f}",
                      f"**{res['Seq1']:.4f}**  ≤ 1.6"],
        })

        st.markdown(f"#### STRESS — POINT 2 (Bottom + shear) {p2}")
        st.table({
            "": ["Sx  =  Mx×ey/Ix/10",
                 "Sy  =  My×ex/Iy/10",
                 "Sfx  =  1.4×F/4/T2²×100",
                 "**Seq = Sx+Sy+0.75×Sfx**"],
            "T/cm²": [f"{res['Sx2']:.4f}",
                      f"{res['Sy2']:.4f}",
                      f"{res['Sfx']:.4f}",
                      f"**{res['Seq2']:.4f}**  ≤ 1.6"],
        })

    with d2:
        dok = "✅" if ok_def else "❌"
        st.markdown(f"#### DEFLECTION {dok}")
        st.table({
            "รายการ": ["D1  —  by load",
                        "D2  —  by hoist weight",
                        "D3  —  by self weight",
                        "L / D1",
                        "L / (D1+D2)",
                        "**L / (D1+D2+D3)**"],
            "ค่า": [f"{res['D1']:.4f} cm",
                    f"{res['D2']:.4f} cm",
                    f"{res['D3']:.4f} cm",
                    f"{res['L_D1']:.0f}",
                    f"{res['L_D1D2']:.0f}",
                    f"**{res['L_D1D2D3']:.0f}**  ≥ 670"],
        })


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — MANUAL CHECK
# ═══════════════════════════════════════════════════════════════════════════════
with tab_manual:
    st.subheader("📐 ระบุขนาดหน้าตัดเอง")
    st.caption("B1 = B − 120 − (T1+T3) ต้องมีค่ามากกว่า 0 เสมอ")

    col1, col2, col3 = st.columns(3)
    with col1:
        B_mm  = st.number_input("B – Top flange width (mm)", value=450, step=25, min_value=150)
        H_mm  = st.number_input("H – Web height (mm)",        value=1040, step=25, min_value=200)
    with col2:
        T1_mm = st.number_input("T1 – Web ซ้าย (mm)",        value=6,  step=1, min_value=4)
        T2_mm = st.number_input("T2 – Top flange (mm)",       value=22, step=1, min_value=4)
    with col3:
        T3_mm = st.number_input("T3 – Web ขวา (mm)",         value=6,  step=1, min_value=4)
        T4_mm = st.number_input("T4 – Bottom flange (mm)",    value=9,  step=1, min_value=4)

    B1_preview = B_mm - 120 - (T1_mm + T3_mm)
    if B1_preview <= 0:
        st.error(f"⚠️ B1 = {B1_preview} mm — ต้องมีค่ามากกว่า 0 กรุณาเพิ่ม B หรือลด T1/T3")
    else:
        st.info(f"B1 (internal width) = **{B1_preview} mm**")

    if st.button("🔍 คำนวณหน้าตัดนี้", use_container_width=True,
                 disabled=(B1_preview <= 0)):
        try:
            sec = compute_section(
                B_mm, H_mm, T1_mm, T2_mm, T3_mm, T4_mm,
                Str=Str_in, Cr=Cr_in, Wep=Wep_in, x=x_in, Rail=int(Rail_in),
            )
            compute_weight(sec, SPAN_m)
            res = compute_checks(sec, LOAD, SPAN_m, W_HOIST)
            st.divider()
            show_results(sec, res)
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — AUTO-OPTIMIZE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_auto:
    st.subheader("🚀 ค้นหาขนาดที่ดีที่สุดอัตโนมัติ")
    st.info(
        "โปรแกรมจะวนลูปทดสอบขนาด B × H และความหนาแผ่น "
        "โดยเลือกขนาดที่ **น้ำหนักเบาที่สุด** ที่ผ่านทั้ง 2 เงื่อนไข\n\n"
        "หมายเหตุ: T1 = T3 (สมมติ web หนาเท่ากัน), T2 อาจต่างจาก T4 ได้"
    )

    ca, cb = st.columns(2)
    with ca:
        H_min_in = st.number_input("H min (mm)", value=400,  step=25, min_value=200)
        H_max_in = st.number_input("H max (mm)", value=1800, step=25, min_value=400)
    with cb:
        B_min_in = st.number_input("B min (mm)", value=200, step=25, min_value=150)
        B_max_in = st.number_input("B max (mm)", value=800, step=25, min_value=200)

    if st.button("🚀 เริ่มค้นหา", use_container_width=True):
        T_flange = [6, 8, 9, 10, 12, 14, 16, 19, 22, 25, 28, 32]
        T_web    = [6, 8, 9, 10, 12, 14]

        best, best_wg = None, 1e9
        H_steps = list(range(int(H_min_in), int(H_max_in)+1, 25))
        total   = len(H_steps)

        with st.spinner("⏳ กำลังวนลูปคำนวณ..."):
            progress = st.progress(0, text="กำลังคำนวณ...")
            for i, H in enumerate(H_steps):
                progress.progress((i+1)/total, text=f"ทดสอบ H = {H} mm …")
                for B in range(int(B_min_in), int(B_max_in)+1, 25):
                    if B - 120 - 24 <= 0:
                        continue
                    if B > H * 0.80 or B < H * 0.15:
                        continue
                    for T2 in T_flange:
                        for T4 in T_flange:
                            for Tw in T_web:
                                try:
                                    sec = compute_section(
                                        B, H, Tw, T2, Tw, T4,
                                        Str=Str_in, Cr=Cr_in, Wep=Wep_in,
                                        x=x_in, Rail=int(Rail_in),
                                    )
                                    if sec['B1'] <= 0:
                                        continue
                                    compute_weight(sec, SPAN_m)
                                    res = compute_checks(sec, LOAD, SPAN_m, W_HOIST)
                                    _, _, _, passed = check_criteria(res)
                                    if passed and sec['Wg'] < best_wg:
                                        best_wg = sec['Wg']
                                        best = (sec, res)
                                except Exception:
                                    continue
            progress.empty()

        if best:
            sec, res = best
            st.success(
                f"✅ พบขนาดที่ดีที่สุด: "
                f"**B={sec['B']:.0f} × H={sec['H']:.0f} mm** | "
                f"T1=T3={sec['T1']:.0f} mm | T2={sec['T2']:.0f} mm | T4={sec['T4']:.0f} mm"
            )
            st.divider()
            show_results(sec, res)
        else:
            st.error("❌ ไม่พบขนาดที่ผ่านเกณฑ์ กรุณาขยายช่วง H/B")


# ── Footer
st.divider()
st.caption(
    "อ้างอิง: Single_girder.xlsx (For_European Hoist) | SS400 | E = 2,100 T/cm² | "
    "เกณฑ์: Stress ≤ 1.6 T/cm² | L/(D1+D2+D3) ≥ 670"
)
