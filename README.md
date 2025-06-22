# 🚀 AutoBit: 모던 암호화폐 자동매매 GUI

**AutoBit**은 PyQt6 기반의 직관적인 GUI를 제공하는 암호화폐 자동매매 프로그램입니다.  
업비트 API를 활용하여 비트코인의 가격을 실시간으로 추적하고, 3가지 전략(공격적 / 안전 / 균형)에 따라 자동 매매를 수행합니다.

---

## ✨ 주요 기능

- 🧠 **3가지 전략 지원**: 공격적 / 안전 / 균형
- 📈 실시간 시세 & 잔액 표시
- 🔄 PyUpbit API 통신
- 💡 자동 거래 쓰레드 기반
- 🔌 네트워크 상태 실시간 확인
- 🧰 API 키 설정 저장
- 🌙 **다크 모드** GUI 인터페이스

---

## 📦 설치 방법

```bash
pip install -r requirements.txt
```

또는 직접 설치:

```bash
pip install pyupbit PyQt6
```

---

## ▶️ 실행 방법

```bash
python autobit.py
```

---

## 📋 사용법

1. Upbit API 키와 시크릿 키를 입력합니다.
2. [API 연결] 버튼으로 정상 연결을 확인합니다.
3. 전략을 선택합니다: `공격적`, `안전`, `균형`
4. [거래 시작] 버튼을 누르면 자동매매가 시작됩니다.

---

## 🧠 전략 설명

| 전략     | 조건 및 방식 |
|----------|--------------|
| 공격적   | 급락 시 매수 비율 50% |
| 안전     | 완만한 상승 시 보유량 전량 매도 |
| 균형     | 변동성 기준 부분 매수/매도 반복 |

---

## ⚖️ 라이선스 / License

```
본 프로젝트는 아래 조건을 따릅니다:

- 개인적 / 비상업적 용도로 자유롭게 사용하실 수 있습니다.
- 모든 사용 시 반드시 원작자(Minjae Developer)를 명시해 주세요.
- 상업적 이용은 허가 없이 불가하며, 별도 서면 허가가 필요합니다.
- 문의: minjae.dev@example.com

This project is licensed under a custom license:

- Free to use for personal and non-commercial purposes.
- Attribution to the original author (Minjae Developer) is required.
- Commercial use is prohibited without explicit written permission.
- Contact: minjae.dev@example.com
```

> 자세한 내용은 [LICENSE](./LICENSE) 파일을 확인하세요.

---

## 📫 연락

질문, 피드백, 상업적 라이선스 문의는 아래 이메일로 부탁드립니다:

**📨 minjae.dev@example.com**

---

## 🛡️ 책임 면책

이 소프트웨어는 “있는 그대로(As-Is)” 제공됩니다.  
이용 중 발생한 손해나 문제에 대해 개발자는 책임지지 않습니다.
