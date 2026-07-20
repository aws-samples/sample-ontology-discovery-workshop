---
ontoforge_form: 1
stage: data_grounding
status: draft
language: ko
---

# 6. 실제 데이터 구조 연결

확인한 스키마·헤더·API 필드만 적고, 없는 필드를 추측하지 마세요. 민감한 실제
레코드 대신 구조와 마스킹된 예시를 사용하세요. 작성 후 `작성 완료`라고 알려주세요.

<!-- ONTOFORGE:SERVER-STATE:START -->
> 서버 상태는 플러그인의 form sync 명령이 갱신합니다.
<!-- ONTOFORGE:SERVER-STATE:END -->

## 데이터 소스와 실제 필드 구조
<!-- REQUIRED:data_sources -->
<!-- 소스명 / 유형 / owner / freshness / sensitivity / field:type 목록 -->


## 소스 필드에서 모델 요소로의 매핑
<!-- REQUIRED:mappings -->
<!-- source.field -> Entity.property 또는 Relation.property / available·partial·missing·derived·unknown -->


## 식별 키와 조인 경로


## 누락·불명확 데이터와 담당자
<!-- REQUIRED:gap_actions -->
<!-- 누락이 없으면 '없음'. 있으면 항목 / 후속 조치 / owner를 적으세요. -->


## 보존·마스킹·접근 제약
