# Local browser libraries

브라우저는 CDN에 접속하지 않습니다. 다음 순서의 번들이 필요합니다.

| 파일 | 패키지 / 고정 버전 |
|---|---|
| `cytoscape.min.js` | `cytoscape@3.28.1` |
| `layout-base.min.js` | `layout-base@2.0.1` |
| `cose-base.min.js` | `cose-base@2.2.0` |
| `cytoscape-fcose.min.js` | `cytoscape-fcose@2.2.0` |
| `cytoscape-cose-bilkent.min.js` | `cytoscape-cose-bilkent@4.1.0` |

이 파일명은 기존 설치 호환을 유지합니다. `.min.js` 확장자여도 일부 배포 파일은 minified가 아닙니다. `layout-base` 없이 `cose-base`를 읽으면 두 레이아웃이 함께 실패하므로 설치 검사에 포함합니다.

누락 파일 설치: `bash scripts/install.sh --target=all --with-libs --no-hook`. 네트워크가 없는 환경에서는 위 고정 버전의 배포 파일을 복사하세요. 서버 실행 중 다운로드하지 않습니다.

모두 MIT 라이선스입니다. SVG 내보내기는 자체 코드로 작성했으며 추가 SVG 확장을 번들하지 않습니다. 라이브러리 코드는 패키지 배포본 그대로 유지합니다.
