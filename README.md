# Instagram Clone

간단한 Instagram 클론 애플리케이션입니다. Python Flask와 SQLite3를 사용하여 구현되었습니다.

## 주요 기능

- **로그인 기능**: 자체 로그인 시스템 (회원가입, 로그인, 로그아웃)
- **게시물 업로드**: 사진과 글을 업로드할 수 있습니다
- **공개 피드**: 팔로우 관계 없이 모든 사용자의 게시물을 볼 수 있습니다

## 설치 및 실행

### 1. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 애플리케이션 실행

```bash
python app.py
```

애플리케이션이 `http://localhost:5000`에서 실행됩니다.

## 데이터베이스

- SQLite3 데이터베이스를 사용합니다
- 첫 실행 시 자동으로 `instagram.db` 파일과 필요한 테이블이 생성됩니다
- `schema.sql` 파일에 데이터베이스 스키마가 정의되어 있습니다

## 프로젝트 구조

```
instagram_clone/
├── app.py                 # Flask 메인 애플리케이션
├── schema.sql             # 데이터베이스 스키마
├── requirements.txt       # Python 패키지 의존성
├── templates/            # HTML 템플릿
│   ├── login.html        # 로그인 페이지
│   ├── signup.html       # 회원가입 페이지
│   ├── feed.html         # 피드 페이지
│   └── upload.html       # 업로드 페이지
└── static/               # 정적 파일 (업로드된 이미지)
    └── uploads/          # 업로드된 이미지 저장 폴더
```

## 사용 방법

1. **회원가입**: `/signup` 페이지에서 새 계정을 만듭니다
2. **로그인**: `/login` 페이지에서 로그인합니다
3. **피드 보기**: 로그인 후 자동으로 피드 페이지로 이동합니다
4. **게시물 업로드**: 헤더의 "업로드" 버튼을 클릭하여 사진과 글을 업로드합니다
5. **로그아웃**: 헤더의 "로그아웃" 버튼을 클릭합니다

## 보안 참고사항

- 프로덕션 환경에서는 `app.py`의 `secret_key`를 변경해야 합니다
- 비밀번호는 Werkzeug의 `generate_password_hash`로 해시화되어 저장됩니다
- 파일 업로드는 `secure_filename`으로 안전하게 처리됩니다

