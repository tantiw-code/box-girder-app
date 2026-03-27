"""
CALCULATION SHEET FOR BOX UP DOUBLE GIRDER
สูตรตรงกับ Excel Double_box_up.xlsx (Walk way sheet) และ PDF Cal.pdf
ตรวจสอบแล้ว: ทุกค่าตรงกับ PDF 100%
"""

import streamlit as st
import math

# ═══════════════════════════════════════════════════════════════════════════════
#  CORE CALCULATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_section(B, H, T1, T2, T3, T4, D=50.0, C=50.0, B2=50.0,
                    Str=6.0, Cr=40.0, Web=8.0, x=50.0, Rail=4):
    """
    คำนวณ Section Properties ของ Box Girder 1 ตัว (Walkway type)
    Input  : มิติทั้งหมดเป็น mm
    Output : dict (A=cm², Ix/Iy=cm⁴, ey/ex=mm, Wg=ton/m, ...)

    สูตรอ้างอิง: Excel Walk way (Ori) sheet
    ─────────────────────────────────────────────────────────────────
    B   = ความกว้างหน้าตัด             T1  = ความหนา Web ซ้าย
    H   = ความสูงหน้าตัด              T2  = ความหนา Top Flange
    T3  = ความหนา Web ขวา            T4  = ความหนา Bottom Flange
    D   = ความสูง Stiffener           C   = ความกว้าง Stiffener
    B2  = ระยะ Edge → Web (50mm)    B1  = ความกว้างภายใน
    Str = ความหนาแผ่น Stringer       Cr  = ความสูง Crane Rail
    Web = ความหนา Web plank          x   = ความกว้าง Web plank
    Rail= จำนวน Rail
    """
    B1 = B - (2 * B2) - (T1 + T3)          # Excel U25
    R  = 2.0 * (C + T4)                     # Excel Y29 = 2*(C+T4)

    # ── Area [cm²] ── Excel Y13
    A = (D * C + B * T2 + B * T4 + T1 * H + T3 * H) / 100.0

    # ── Wg [ton/m] ── Excel Y15 (Walk version รวม walkway)
    Wg = (T2*B + T4*B + T3*(H+Cr) + T1*(H+Cr) + Str*B1 + Web*x*Rail) * 8.1 / 1e6

    # ── Centroid ey จากด้านล่าง [mm] ── Excel Y19
    ey = (
        B  * T2 * (H + 0.5*T2) +
        T3 * 0.5 * H**2 +
        T1 * 0.5 * H**2 -
        B  * 0.5 * T4**2 -
        D  * C  * (0.5*C + T4)
    ) / (A * 100.0)

    # ── Centroid ex จากด้านซ้าย [mm] ── Excel Y17
    ex = (
        B  * T4 * (0.5*B - B2) +
        B  * T2 * (0.5*B - B2) +
        H  * T3**2 * 0.5 +
        H  * T1 * (T3 + B1 + 0.5*T1) +
        C  * D  * 0.5 * T3
    ) / (A * 100.0)

    # ── Ix [cm⁴] ── Excel Y21
    Ix = (
        (B*T4**3/12) + B*T4 * (ey + T4/2)**2 +
        (B*T2**3/12) + B*T2 * ((H + 0.5*T2) - ey)**2 +
        (T1*H**3/12) + T1*H * (0.5*H - ey)**2 +
        (T3*H**3/12) + T3*H * (0.5*H - ey)**2 +
        (D*C**3/12)  + D*C  * (ey + T4 + 0.5*C)**2
    ) / 1e4

    # ── Iy [cm⁴] ── Excel Y23
    Iy = (
        (T4*B**3/12) + T4*B * (B/2 - B2 - ex)**2 +
        (T2*B**3/12) + T2*B * (0.5*B - B2 - ex)**2 +
        (H*T3**3/12) + H*T3 * (ex - 0.5*T3)**2 +
        (H*T1**3/12) + H*T1 * (B1 + T3 + 0.5*T1 - ex)**2 +
        (C*D**3/12)  + C*D  * (ex - 0.5*T3)**2
    ) / 1e4

    return dict(
        A=A, Wg=Wg, ey=ey, ex=ex, Ix=Ix, Iy=Iy,
        B1=B1, R=R,
        B=B, H=H, T1=T1, T2=T2, T3=T3, T4=T4,
        D=D, C=C, B2=B2,
        Str=Str, Cr=Cr, Web=Web, x=x, Rail=Rail,
    )


def compute_checks(sec, LOAD, SPAN_m, W_HOIST, WHEELBASE_mm):
    """
    คำนวณ Bending Moment / Stress / Deflection ต่อ 1 girder
    (ใช้ full load ตามสูตร Excel — ไม่หาร 2 สำหรับ Mx และ Sr)

    สูตรตรวจสอบจาก PDF Cal.pdf ทุกค่า:
      Mx_load, Mx_wt, Sx, Sy, Sr, Seq, D1, D2, D3, L/D ✓
    """
    E     = 2100.0                      # Young's Modulus [Ton/cm²]
    L_cm  = SPAN_m * 100.0              # span [cm]
    La_cm = WHEELBASE_mm / 10.0         # wheelbase [cm]

    Ix, Iy   = sec['Ix'], sec['Iy']
    Wg       = sec['Wg']
    ey, ex   = sec['ey'], sec['ex']
    T1,T2,T3,T4 = sec['T1'],sec['T2'],sec['T3'],sec['T4']
    B, H, B2, R  = sec['B'], sec['H'], sec['B2'], sec['R']

    # ── Bending Moment ── Excel H42, H46, H50, H54
    # Mx by load = (F/4L)*(L−La/2)²  where F = 0.75*(LOAD+W_HOIST)
    Mx_load   = 0.75*(LOAD + W_HOIST) / (4.0 * L_cm) * (L_cm - La_cm/2.0)**2

    # Mx by weight = 1.1*Wg*L(m)*L(cm)/8
    Mx_weight = 1.1 * Wg * SPAN_m * L_cm / 8.0

    Mx = Mx_load + Mx_weight
    My_factor = 0.10 if SPAN_m > 26 else 0.05
    My = My_factor * Mx

    # ── STRESS POINT 1 ── Excel S42, S46, S50, S54
    Sx1  = Mx * (ey + T4) / Ix / 10.0                       # bending top-bottom
    Sy1  = My * (ex + B2) / Iy / 10.0                       # bending left-right
    Sr   = (LOAD + W_HOIST) / (2.0 * T3 * R) * 100.0        # shear
    Seq1 = math.sqrt(Sx1**2 + Sr**2 - Sx1*Sr) + Sy1         # combined

    # ── STRESS POINT 2 ── Excel AA42, AA46, AA50
    Sx2  = Mx * (H - ey + T2) / Ix / 10.0
    Sy2  = My * (B - ex - B2) / Iy / 10.0
    Seq2 = Sx2 + Sy2

    # ── DEFLECTION ── Excel AI42, AI46, AI50
    # D1 by load (2-point loads):  P/48*E*Ix*(L−La)*(3L²−(L−La)²)
    D1 = (0.25 * LOAD / (48.0 * E * Ix)) * (L_cm - La_cm) * (3*L_cm**2 - (L_cm - La_cm)**2)

    # D2 by hoist weight (mid-span point):  Wh/2 * L³/(48*E*Ix)
    D2 = (W_HOIST / 2.0 * L_cm**3) / (48.0 * E * Ix)

    # D3 by self weight (UDL):  5*Wg*L(m)*L(cm)³/(384*E*Ix)
    D3 = 5.0 * Wg * SPAN_m * L_cm**3 / (384.0 * E * Ix)

    D_total = D1 + D2 + D3
    L_D1      = L_cm / D1        if D1      > 0 else 9999
    L_D1D2    = L_cm / (D1+D2)   if D1+D2   > 0 else 9999
    L_D1D2D3  = L_cm / D_total   if D_total > 0 else 9999

    IyIx_pct  = Iy / Ix * 100.0

    return dict(
        Mx_load=Mx_load, Mx_weight=Mx_weight, Mx=Mx, My=My,
        Sx1=Sx1, Sy1=Sy1, Sr=Sr, Seq1=Seq1,
        Sx2=Sx2, Sy2=Sy2, Seq2=Seq2,
        D1=D1, D2=D2, D3=D3,
        L_D1=L_D1, L_D1D2=L_D1D2, L_D1D2D3=L_D1D2D3,
        IyIx_pct=IyIx_pct,
    )


def check_criteria(res):
    """
    ตรวจสอบเงื่อนไขทั้ง 3 ข้อ
    1. Iy/Ix ≈ 10–16 %     (เป้าหมาย ~12 %)
    2. Seq1 & Seq2 ≤ 1.6   (Ton/cm²)
    3. L/(D1+D2+D3) ≥ 700
    """
    ok_iy  = 10.0 <= res['IyIx_pct'] <= 16.0
    ok_str = res['Seq1'] <= 1.6 and res['Seq2'] <= 1.6
    ok_def = res['L_D1D2D3'] >= 700
    return ok_iy, ok_str, ok_def, (ok_iy and ok_str and ok_def)


def find_best(LOAD, SPAN_m, W_HOIST, WHEELBASE_mm,
              Str=6.0, Cr=40.0, Web=8.0, x=50.0, Rail=4):
    """
    วนหาหน้าตัดที่ผ่านเงื่อนไขทั้งหมด โดยเลือกขนาดที่น้ำหนักเบาที่สุด
    """
    H_range = range(400, 1801, 25)
    B_range = range(200, 801, 25)
    T_list  = [6, 8, 9, 10, 12, 14, 16, 19, 22, 25]

    best, best_wg = None, 1e9

    for H in H_range:
        for B in B_range:
            if B > H * 0.75 or B < H * 0.20:
                continue
            for Tf in T_list:
                for Tw in T_list:
                    try:
                        sec = compute_section(B, H, Tf, Tf, Tw, Tw,
                                              Str=Str, Cr=Cr, Web=Web, x=x, Rail=Rail)
                        res = compute_checks(sec, LOAD, SPAN_m, W_HOIST, WHEELBASE_mm)
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
    page_title="Box Girder Designer",
    page_icon="🏗️",
    layout="wide",
)

st.title("🏗️ CALCULATION SHEET — BOX UP DOUBLE GIRDER")
st.caption("สูตรตรงกับ Excel + PDF Cal.pdf 100% | SS400 | E = 2,100 T/cm²")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_manual, tab_auto = st.tabs(["📋 Manual Check", "🚀 Auto-Optimize"])


# ─── SHARED INPUT (sidebar) ───────────────────────────────────────────────────
with st.sidebar:
    st.header("📥 ข้อมูลโครงการ")
    LOAD         = st.number_input("Load (Ton)",            value=15.0, step=0.5,  min_value=1.0)
    SPAN_m       = st.number_input("Span (m)",              value=20.0, step=0.5,  min_value=1.0)
    W_HOIST      = st.number_input("Weight of Hoist (Ton)", value=3.1,  step=0.1,  min_value=0.1)
    WHEELBASE_mm = st.number_input("Wheelbase La (mm)",     value=2100.0,step=50.0,min_value=100.0)

    st.divider()
    st.header("🚶 Walkway Parameters")
    Str_in  = st.number_input("Str – Stringer thickness (mm)", value=6.0,  step=1.0)
    Cr_in   = st.number_input("Cr – Crane rail height (mm)",   value=40.0, step=5.0)
    Web_in  = st.number_input("Web – Plank thickness (mm)",    value=8.0,  step=1.0)
    x_in    = st.number_input("x – Plank width (mm)",          value=50.0, step=5.0)
    Rail_in = st.number_input("Rail – จำนวน (ea)",             value=4,    step=1, min_value=1)

    st.divider()
    st.header("📐 Fixed Parameters")
    D_in  = st.number_input("D – Stiffener height (mm)", value=50.0, step=5.0)
    C_in  = st.number_input("C – Stiffener width (mm)",  value=50.0, step=5.0)
    B2_in = st.number_input("B2 – Edge to web (mm)",     value=50.0, step=5.0)


# ─── HELPER: display result ───────────────────────────────────────────────────
def show_results(sec, res):
    ok_iy, ok_str, ok_def, passed = check_criteria(res)

    # ── Summary badge
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
    k1.metric("Iy/Ix",
              f"{res['IyIx_pct']:.2f} %",
              delta="เกณฑ์ 10–16 %",
              delta_color="normal" if ok_iy  else "inverse")
    k2.metric("Max Stress  (P1 & P2)",
              f"{max(res['Seq1'], res['Seq2']):.3f}  T/cm²",
              delta="เกณฑ์ ≤ 1.6 T/cm²",
              delta_color="normal" if ok_str else "inverse")
    k3.metric("L / (D1+D2+D3)",
              f"{res['L_D1D2D3']:.0f}",
              delta="เกณฑ์ ≥ 700",
              delta_color="normal" if ok_def else "inverse")

    st.divider()

    # ── Section + Properties + Moment
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 📏 ขนาดหน้าตัด")
        st.table({
            "พารามิเตอร์": ["B","H","T1 (Web L)","T2 (Top flange)",
                             "T3 (Web R)","T4 (Bot flange)","B1","D","C"],
            "ค่า (mm)": [f"{sec['B']:.0f}", f"{sec['H']:.0f}",
                          f"{sec['T1']:.0f}", f"{sec['T2']:.0f}",
                          f"{sec['T3']:.0f}", f"{sec['T4']:.0f}",
                          f"{sec['B1']:.0f}", f"{sec['D']:.0f}", f"{sec['C']:.0f}"],
        })

    with c2:
        st.markdown("#### 📊 Section Properties")
        st.table({
            "สัญลักษณ์": ["A","Wg/girder","ey","ex","Ix","Iy","Iy/Ix","R"],
            "ค่า": [
                f"{sec['A']:.2f} cm²",
                f"{sec['Wg']*1000:.2f} kg/m",
                f"{sec['ey']:.2f} mm",
                f"{sec['ex']:.2f} mm",
                f"{sec['Ix']:,.2f} cm⁴",
                f"{sec['Iy']:,.2f} cm⁴",
                f"{res['IyIx_pct']:.2f} %",
                f"{sec['R']:.0f} mm",
            ],
        })

    with c3:
        st.markdown("#### 🔩 Bending Moment")
        st.table({
            "รายการ": ["Mx by load","Mx by weight","Mx total","My"],
            "ค่า (Ton-cm)": [
                f"{res['Mx_load']:.2f}",
                f"{res['Mx_weight']:.2f}",
                f"{res['Mx']:.2f}",
                f"{res['My']:.2f}",
            ],
        })

    st.divider()

    # ── Stress + Deflection
    d1, d2 = st.columns(2)

    with d1:
        p1 = "✅" if res['Seq1'] <= 1.6 else "❌"
        p2 = "✅" if res['Seq2'] <= 1.6 else "❌"
        iy = "✅" if ok_iy else "❌"

        st.markdown(f"#### STRESS — POINT 1 {p1}")
        st.table({
            "": ["Sx","Sy","Sr (shear)","**Seq**"],
            "Ton/cm²": [
                f"{res['Sx1']:.3f}",
                f"{res['Sy1']:.3f}",
                f"{res['Sr']:.3f}",
                f"**{res['Seq1']:.3f}**  ≤ 1.6",
            ],
        })

        st.markdown(f"#### STRESS — POINT 2 {p2}")
        st.table({
            "": ["Sx","Sy","**Seq**"],
            "Ton/cm²": [
                f"{res['Sx2']:.3f}",
                f"{res['Sy2']:.3f}",
                f"**{res['Seq2']:.3f}**  ≤ 1.6",
            ],
        })

        st.info(f"**Iy/Ix = {res['IyIx_pct']:.2f} %** {iy}   (เกณฑ์ 10–16 %)")

    with d2:
        dok = "✅" if ok_def else "❌"
        st.markdown(f"#### DEFLECTION {dok}")
        st.table({
            "รายการ": [
                "D1 — by load",
                "D2 — by hoist weight",
                "D3 — by self weight",
                "L / D1",
                "L / (D1+D2)",
                "**L / (D1+D2+D3)**",
            ],
            "ค่า": [
                f"{res['D1']:.4f} cm",
                f"{res['D2']:.4f} cm",
                f"{res['D3']:.4f} cm",
                f"{res['L_D1']:.0f}",
                f"{res['L_D1D2']:.0f}",
                f"**{res['L_D1D2D3']:.0f}**  ≥ 700",
            ],
        })


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — MANUAL CHECK
# ═══════════════════════════════════════════════════════════════════════════════
with tab_manual:
    st.subheader("📐 ระบุขนาดหน้าตัดเอง")

    c1, c2, c3 = st.columns(3)
    with c1:
        B_mm  = st.number_input("B – ความกว้าง (mm)",      value=400, step=25, min_value=100)
        H_mm  = st.number_input("H – ความสูง (mm)",        value=1030, step=25, min_value=200)
    with c2:
        T1_mm = st.number_input("T1 – Web ซ้าย (mm)",      value=6,  step=1, min_value=4)
        T2_mm = st.number_input("T2 – Top flange (mm)",    value=8,  step=1, min_value=4)
    with c3:
        T3_mm = st.number_input("T3 – Web ขวา (mm)",       value=6,  step=1, min_value=4)
        T4_mm = st.number_input("T4 – Bottom flange (mm)", value=8,  step=1, min_value=4)

    if st.button("🔍 คำนวณหน้าตัดนี้", use_container_width=True):
        try:
            sec = compute_section(
                B_mm, H_mm, T1_mm, T2_mm, T3_mm, T4_mm,
                D=D_in, C=C_in, B2=B2_in,
                Str=Str_in, Cr=Cr_in, Web=Web_in, x=x_in, Rail=int(Rail_in),
            )
            res = compute_checks(sec, LOAD, SPAN_m, W_HOIST, WHEELBASE_mm)
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
        "โดยเลือกขนาดที่**น้ำหนักเบาที่สุด**ที่ผ่านทั้ง 3 เงื่อนไข"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        H_min = st.number_input("H min (mm)", value=400,  step=25, min_value=200)
        H_max = st.number_input("H max (mm)", value=1800, step=25, min_value=400)
    with col_b:
        B_min = st.number_input("B min (mm)", value=200, step=25, min_value=100)
        B_max = st.number_input("B max (mm)", value=800, step=25, min_value=200)

    if st.button("🚀 เริ่มค้นหา", use_container_width=True):
        with st.spinner("⏳ กำลังวนลูปคำนวณ... (อาจใช้เวลา 20–60 วินาที)"):

            T_list = [6, 8, 9, 10, 12, 14, 16, 19, 22, 25]
            best, best_wg = None, 1e9

            progress = st.progress(0, text="กำลังคำนวณ...")
            H_steps = list(range(int(H_min), int(H_max)+1, 25))
            total = len(H_steps)

            for i, H in enumerate(H_steps):
                progress.progress((i+1)/total, text=f"ทดสอบ H = {H} mm …")
                for B in range(int(B_min), int(B_max)+1, 25):
                    if B > H * 0.75 or B < H * 0.20:
                        continue
                    for Tf in T_list:
                        for Tw in T_list:
                            try:
                                sec = compute_section(
                                    B, H, Tf, Tf, Tw, Tw,
                                    D=D_in, C=C_in, B2=B2_in,
                                    Str=Str_in, Cr=Cr_in, Web=Web_in,
                                    x=x_in, Rail=int(Rail_in),
                                )
                                res = compute_checks(sec, LOAD, SPAN_m, W_HOIST, WHEELBASE_mm)
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
                f"T_flange={sec['T2']:.0f} mm | T_web={sec['T3']:.0f} mm"
            )
            st.divider()
            show_results(sec, res)
        else:
            st.error(
                "❌ ไม่พบขนาดที่ผ่านเกณฑ์ในช่วงที่กำหนด "
                "กรุณาเพิ่มช่วง H/B หรือปรับเงื่อนไข"
            )


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "อ้างอิง: Double_box_up.xlsx (Walk way sheet) + Cal.pdf | "
    "SS400 | E = 2,100 T/cm² | "
    "เกณฑ์: Iy/Ix 10–16 % | Seq ≤ 1.6 T/cm² | L/(D1+D2+D3) ≥ 700"
)