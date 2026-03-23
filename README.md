<div align="center">

# 🎬 대전신세계 돌비시네마 예매 오픈 알림봇

**대전신세계아트앤사이언스 돌비시네마 새 예매가 열리면 텔레그램으로 즉시 알려주는 챗봇**

![Python](https://img.shields.io/badge/Python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white) ![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white) ![aiohttp](https://img.shields.io/badge/aiohttp-2C5BB4?style=for-the-badge&logo=aiohttp&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

</div>

---

## 📌 주요 기능

> **5분마다 자동 체크** | **실시간 텔레그램 알림** | **즉시 조회**

- 🔔 새로운 날짜의 예매가 열리면 **상영 시간표 + 잔여 좌석** 정보를 텔레그램으로 즉시 발송
- 🗂 이미 알림을 보낸 날짜는 DB에 기록하여 **중복 알림 방지**
- 💬 텔레그램 챗봇으로 **실시간 예매 현황 조회** 가능

---

## 🤖 챗봇 명령어

| 명령어 | 기능 |
|:------:|------|
| `/start` | 봇 소개 |
| `/help` | 명령어 목록 안내 |
| `/now` | 현재 예매 현황 즉시 조회 |
| `/theaters` | 전국 돌비시네마 8개관 목록 조회 |

---

## 💬 알림 예시

```
🔔 돌비 예매 오픈!

[대전신세계아트앤사이언스] 3월 25일(수)

프로젝트 헤일메리(DOLBY CINEMA [Laser])
  09:30~12:16 313/313석
  12:40~15:26 300/313석
  18:50~21:36 313/313석
  22:00~24:46 313/313석

진격의 거인 완결편 더 라스트 어택(DOLBY CINEMA [Laser])
  15:50~18:24 312/313석

👉 https://www.megabox.co.kr
```

---

## 🏗 아키텍처

```
┌─────────────────┐     5분마다 핑      ┌──────────────────────┐
│  GitHub Actions  │ ──────────────────→ │    Render 서버       │
│  (keep-alive)    │                     │                      │
└─────────────────┘                      │  ┌────────────────┐  │
                                         │  │ 헬스체크 서버   │  │
                                         │  └────────────────┘  │
                                         │                      │
                                         │  ┌────────────────┐  │
                                         │  │ 텔레그램 봇     │  │
                                         │  └───────┬────────┘  │
                                         │          │           │
                                         │  ┌───────▼────────┐  │
                                         │  │ 자동 체크 (5분) │  │
                                         │  └───────┬────────┘  │
                                         │          │           │
                                         │  ┌───────▼────────┐  │
                                         │  │ SQLite DB       │  │
                                         │  └────────────────┘  │
                                         └──────────┬───────────┘
                                                    │
                                    ┌───────────────┼───────────────┐
                                    ▼                               ▼
                            ┌──────────────┐              ┌──────────────┐
                            │ 메가박스 API  │              │ 텔레그램 API │
                            └──────────────┘              └──────────────┘
```

---

## ⚙️ 동작 원리

### 🟢 서버 시작
1. Render에서 `bot.py` 실행
2. SQLite DB 초기화 (테이블이 없으면 자동 생성)
3. 기존 오픈 날짜를 notified 테이블에 등록 (재시작 시 중복 알림 방지)
4. 헬스체크 서버 시작 (Render 슬립 방지용)
5. 텔레그램 봇 시작 (polling 모드로 명령어 대기)
6. 자동 체크 스케줄러 등록 (5분 간격)

### 🔄 자동 체크 사이클 (5분마다)
1. 대전신세계 돌비시네마 메가박스 API에 오픈 날짜 조회
2. 각 날짜별로 DB의 notified 테이블 확인
   - ✅ 이미 알림 보낸 날짜 → 스킵
   - 🆕 새로 열린 날짜 → 시간표 + 잔여좌석 조회 → 포맷팅
3. 텔레그램 알림 발송
4. notified 테이블에 기록 (중복 알림 방지)

### 🏓 Render 슬립 방지
- Render 무료 플랜은 15분간 요청이 없으면 서버가 슬립 모드로 전환됨
- GitHub Actions가 5분마다 헬스체크 엔드포인트에 HTTP 요청을 보내 서버를 깨어있게 유지
- 봇이 24시간 상시 가동되어 자동 체크가 정상 작동

---

## 🗄 DB 구조

### notified
이미 알림을 보낸 극장/날짜 조합을 기록하여 중복 알림을 방지합니다.
```
┌───────────┬───────────┐
│ branch_no │ play_date │
├───────────┼───────────┤
│ 0028      │ 20260320  │  ← 대전 3/20 알림 완료
│ 0028      │ 20260321  │  ← 대전 3/21 알림 완료
└───────────┴───────────┘
```

---

## 📁 프로젝트 구조

```
📦 DAEJEON_DOLBY_ALARM_BOT
├── 🤖 bot.py              # 메인 (명령어 처리 + 자동 체크 스케줄러 + 헬스체크 서버)
├── 🎬 megabox.py          # 메가박스 API 클라이언트 (날짜/시간표 조회, 포맷팅)
├── 🗄 db.py               # SQLite DB (알림 기록 CRUD)
├── 🏢 branches.py         # 전국 돌비시네마 8개관 코드/이름 매핑
├── 📋 requirements.txt    # Python 의존성
├── 🐳 Dockerfile          # 컨테이너 배포용
└── ⚡ .github/workflows/
    └── keep-alive.yml     # Render 슬립 방지 (5분마다 핑)
```
