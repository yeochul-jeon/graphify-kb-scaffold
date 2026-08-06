# Agent Workflow 연습 가이드

## 무엇을 연습하나요?

짧은 요청을 작업지시서로 만들고, 준비 → 작업 중 → 검증 중 → 완료 순서로
상태를 바꾸며, 마지막에 결과보고서를 만드는 과정을 연습합니다.

이 버전은 실제 Claude Code나 Codex를 실행하지 않습니다.
Hermes 전역 설정을 변경하지 않습니다. 기존 프로젝트 파일도 수정하지 않습니다.

## 프로젝트 폴더로 이동

```bash
cd /Users/cjenm/github/graphify-kb
```

## 1. 작업 만들기

```bash
./scripts/agent-workflow create "README 오타를 수정해줘"
```

예상 출력:

```text
작업 T-YYYYMMDD-NNN를 준비했습니다.
다음 명령: ./scripts/agent-workflow start T-YYYYMMDD-NNN
```

화면에 표시된 실제 `T-YYYYMMDD-NNN` 작업 번호를 이후 명령에 사용합니다.

## 2. 현재 상태 보기

```bash
./scripts/agent-workflow show T-20260724-001
```

예상 출력:

```text
현재 상태: 준비
실행 방식: 연습 모드
실제 파일 변경: 없음
```

## 3. 작업 시작 표시

```bash
./scripts/agent-workflow start T-20260724-001
```

예상 출력:

```text
현재 상태: 작업 중
다음 명령: ./scripts/agent-workflow verify T-20260724-001
```

## 4. 검증 시작 표시

```bash
./scripts/agent-workflow verify T-20260724-001
```

예상 출력:

```text
현재 상태: 검증 중
다음 명령: ./scripts/agent-workflow complete T-20260724-001
```

## 5. 완료 처리

```bash
./scripts/agent-workflow complete T-20260724-001
```

예상 출력:

```text
현재 상태: 완료
실제 파일 변경: 없음
다음 명령: 없음
```

## 생성된 파일

- `.agent/tasks/<작업번호>.md`: 작업지시서
- `.agent/runs/<작업번호>.json`: 진행상태
- `.agent/results/<작업번호>.md`: 결과보고서

## 자주 발생하는 오류

상태를 건너뛰면 프로그램이 다음에 실행할 명령을 알려줍니다. 존재하지 않는
작업 번호를 사용하면 먼저 `create`로 작업을 만들도록 안내합니다. 완료된
작업은 다시 덮어쓰지 않습니다.

## 새 작업 연습

기존 연습 파일을 삭제하지 않고 `create` 명령을 다시 실행하세요. 새로운 작업
번호가 자동으로 만들어집니다.

## 후속 Hermes 연결

후속 단계에서는 작업지시서와 결과보고서 형식을 유지하고, 연습 실행 부분만
Hermes 및 Claude Code/Codex 실행기로 교체합니다.
