# SSH 키 인증 설정 가이드

## 원리

비밀번호 인증은 매번 입력이 필요하지만, SSH 키 인증은 **자물쇠(공개키)와 열쇠(개인키)** 방식으로 동작합니다.

```
1. 키 생성
   Mac  →  개인키 (~/.ssh/id_ed25519)     ← 절대 외부 유출 금지
        →  공개키 (~/.ssh/id_ed25519.pub) ← 서버에 등록해도 안전

2. 서버에 공개키 등록
   서버의 ~/.ssh/authorized_keys 에 공개키 추가

3. 이후 접속 시
   Mac이 개인키로 "나 맞아요" 서명
   서버가 공개키로 서명 검증 → 비밀번호 없이 통과
```

공개키는 자물쇠와 같아서 누구에게 줘도 괜찮습니다.
개인키는 열쇠이므로 절대 외부에 공유하지 않습니다.

---

## 설정 순서

### 1. 키 생성 (Mac에서 1회)

```bash
ssh-keygen -t ed25519 -C "visuworks" -f ~/.ssh/id_ed25519 -N ""
```

| 옵션 | 설명 |
|------|------|
| `-t ed25519` | 키 알고리즘 (현재 가장 권장) |
| `-C "visuworks"` | 키에 붙는 코멘트 (식별용) |
| `-f ~/.ssh/id_ed25519` | 저장 경로 |
| `-N ""` | 키 비밀번호 없음 (비워두면 접속 시 아무것도 안 물어봄) |

생성 후 확인:

```bash
ls ~/.ssh/
# id_ed25519      ← 개인키 (비공개)
# id_ed25519.pub  ← 공개키 (서버에 등록할 것)
```

### 2. 서버에 공개키 등록

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub myserver
```

이 명령 한 번에 서버 비밀번호 입력 후 자동으로 `~/.ssh/authorized_keys`에 추가됩니다.
이후로는 비밀번호 없이 접속됩니다.

### 3. 접속 확인

```bash
ssh myserver
# 비밀번호 묻지 않고 바로 접속되면 성공
```

---

## 서버 여러 대에 등록하기

키는 한 번만 만들면 됩니다. 새 서버에 등록할 때마다 `ssh-copy-id`만 반복합니다.

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub myserver
ssh-copy-id -i ~/.ssh/id_ed25519.pub 다른서버alias
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@192.168.1.100
```

---

## ~/.ssh/config 와 조합

`~/.ssh/config`에 서버 alias를 등록해두면 더 편합니다.

```
Host myserver
    HostName ssh.mingyuprojects.dev
    User server
    IdentityFile ~/.ssh/id_ed25519
    ProxyCommand cloudflared access ssh --hostname %h
```

`IdentityFile`을 명시하면 SSH가 어떤 키를 쓸지 헷갈리지 않습니다.

---

## 트러블슈팅

**`ssh-copy-id: ERROR: No identities found`**
→ 키가 없는 것. 1단계 키 생성부터 진행.

**등록했는데도 비밀번호를 물어봄**
→ 서버의 SSH 설정이 키 인증을 허용하지 않는 경우. 서버에서 확인:
```bash
grep PubkeyAuthentication /etc/ssh/sshd_config
# PubkeyAuthentication yes 여야 함
```

**키가 여러 개인데 어떤 걸 쓸지 모르겠음**
```bash
ssh -v myserver 2>&1 | grep "Trying private key"
# 어떤 키를 시도하는지 출력됨
```
