"""Day-one Malay/Manglish smoke test for Nemotron on Token Factory.

Runs 20 real-shaped Malaysian messages through the triage step on each
configured tier and prints the family + confidence side by side, so you can
see within five minutes whether Nemotron handles Bahasa Malaysia well enough
to demo in BM, or whether the demo should be in English/Manglish.

  python scripts/malay_smoke.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jaga.llm import TokenFactory, Usage  # noqa: E402
from jaga.prompts import TRIAGE_SYSTEM, TRIAGE_USER  # noqa: E402
from jaga.schemas import Triage  # noqa: E402

SAMPLES = [
    ("scam/impersonation", "Ini Inspektor Razak dari Bukit Aman. Nama puan terlibat dalam kes pengubahan wang haram. Jangan beritahu sesiapa, sila call balik 011-9999 0101 segera."),
    ("scam/investment", "Peluang terhad! Pelaburan emas Golden Harvest Capital, pulangan 30% sebulan dijamin, berlesen SC. Modal minima RM5,000. WhatsApp 011-9999 0123."),
    ("scam/parcel", "Pos Laju: bungkusan anda ditahan di kastam KLIA. Sila bayar yuran RM48 di poslaju-kastam.xyz untuk pelepasan dalam 24 jam."),
    ("scam/phishing_otp", "Maybank: Akaun anda akan disekat. Sila kemaskini dan sahkan TAC di maybank2u-secure-verify.xyz sekarang."),
    ("scam/mule", "Nak buat duit mudah? Sewa akaun bank anda RM800 seminggu, komisen setiap transaksi. PM saya."),
    ("scam/love", "Sayang, saya dah hantar hadiah dari London tapi kastam minta RM2,300. Boleh tolong bayar dulu? Rindu you."),
    ("legit/hard", "Maybank tidak akan sekali-kali meminta TAC anda melalui telefon atau SMS. Jangan kongsi TAC dengan sesiapa."),
    ("legit/hard", "Puan, ini Faizal dari Prudential. Premium polis puan jatuh tempo 20 Okt. Boleh saya call esok pagi untuk sahkan? 012-345 6789"),
    ("legit", "Mak, Siti nak transfer RM200 untuk duit pasar esok ya. Jangan lupa ambil ubat."),
    ("legit", "Klinik Lim: temujanji Puan Aminah pada 18/10 jam 10 pagi. Balas Y untuk sahkan."),
    ("scam/impersonation", "LHDN: Anda mempunyai tunggakan cukai RM3,450. Waran tangkap akan dikeluarkan hari ini jika tidak dijelaskan. Hubungi pegawai kami 011-0000 2211."),
    ("scam/phishing_otp", "Your TNG eWallet has been suspended. Verify now at tng-ewallet-verify.top to avoid permanent closure."),
    ("scam/investment", "Auntie, my uncle's forex group confirm profit one, last month I got RM4k already lah. Join link: fx-pro-signal.club"),
    ("scam/parcel", "J&T Express: parcel on hold, customs fee RM35 required. Pay here jnt-release.icu within 12 hours."),
    ("legit/hard", "J&T Express: parcel MY123456789 out for delivery today. Rider: Ah Seng 017-xxx xxxx. No payment required."),
    ("legit", "Reminder: Mesyuarat PIBG sekolah pada Sabtu ini jam 9 pagi di dewan. Terima kasih."),
    ("scam/mule", "Hiring part-time 'payment agent'. Just receive money into your account and transfer out, keep 5%. No experience needed. Apply now."),
    ("legit/hard", "Grab: Your ride to KLCC is RM18.50. Pay with GrabPay or cash. Driver arriving in 3 min."),
    ("scam/love", "Dear, I'm a US army doctor in Syria. I want to send you my savings for safekeeping, just pay the courier insurance RM1,500 first."),
    ("legit", "Hi Mum, dinner at Auntie Mei's place 7pm Sunday. Can you bring the kuih? Love you."),
]


def main() -> None:
    tf = TokenFactory()
    if tf.mock:
        print("NOTE: running in mock mode (no NEBIUS_API_KEY) — this only exercises the heuristics.\n")
    roles = ["fast", "plan"]
    print(f"{'expected':20s} | " + " | ".join(f"{r:28s}" for r in roles))
    print("-" * 90)
    usage = Usage()
    for expected, text in SAMPLES:
        outs = []
        for role in roles:
            try:
                t = tf.structured(role, TRIAGE_SYSTEM, TRIAGE_USER.format(channel="whatsapp", text=text), Triage,
                                  thinking=False, usage=usage, context={"text": text})
                outs.append(f"{t.family:14s} {t.confidence:.2f} {t.language}")
            except Exception as e:  # noqa: BLE001
                outs.append(f"ERR {str(e)[:22]}")
        print(f"{expected:20s} | " + " | ".join(f"{o:28s}" for o in outs))
    print("\nusage:", json.dumps(usage.as_dict()), f"cost ${usage.cost_usd:.4f}")
    print("\nRead across: if 'fast' gets the Malay rows right, demo in BM. If only 'plan' does, route BM to Super.")


if __name__ == "__main__":
    main()
