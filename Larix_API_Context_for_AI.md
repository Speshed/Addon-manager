# Larix EST.WebApi — контекст и справочник для другого ChatGPT/агента

> **Назначение файла:** передай этот файл другому чату вместе с задачей. Он содержит восстановленную схему локального API Larix, правила авторизации, формат запросов, DTO и описание endpoint'ов. Информация получена из декомпилированных сборок `EST.WebApi` и `EST.WebApi.Models`, а часть поведения подтверждена реальными запросами к локальному серверу.

## 1. Что это за API

- Локальный backend Larix работает через HTTP на `http://localhost:5000`.
- Backend-процесс: `EST.WebApi.exe`.
- Клиент может быть полностью внешним: Python, PySide6, PowerShell, C#, другой процесс.
- GUI `Manager.exe` не обязан выполнять сам запрос: внешний клиент может обращаться к `EST.WebApi` напрямую, пока backend запущен.
- API **внутренний и недокументированный**, поэтому после обновления Larix маршруты/DTO/права могут измениться.

## 2. Правила для ИИ, который будет использовать этот файл

1. Не придумывать endpoint'ы, поля DTO и значения enum, которых нет в этом файле.
2. Для чтения предпочитать `GET` и явно безопасные методы.
3. `POST`, `PUT`, `DELETE`, а также `GET` с семантикой `run/start/reset/clear/build/adapt` считать потенциально изменяющими состояние.
4. Перед генерацией изменяющего запроса обязательно объяснить, что он меняет.
5. Использовать Bearer JWT после `/auth`, если endpoint требует авторизации.
6. JSON отправлять в camelCase. ASP.NET Core принимает регистр свойств достаточно гибко, но канонический формат здесь — camelCase.
7. Если DTO ссылается на внешний тип, схема которого не восстановлена, не выдумывать его поля.
8. Для диагностики версии сначала можно вызвать `/getApiVersion`.
9. Всегда использовать `timeout` в HTTP-клиенте и `raise_for_status()`/эквивалент.

## 3. Подтверждённая авторизация

Для локального адреса `http://localhost:5000/` оригинальный Manager использует логин/пароль `Test` / `Test`.

### 3.1 POST `/auth`

Пример тела:

```json
{
  "userAuthDto": {
    "login": "Test",
    "password": "Test"
  },
  "terminalSessionRequest": {
    "hostTitle": "<DOMAIN\\USER@COMPUTER>",
    "hostIdent": "<Base64 SHA512(hostTitle)>",
    "applicationCode": "LarixLLC\\Larix\\Est\\Manager",
    "destination": "<AES-CBC encrypted http://localhost:5000/>"
  }
}
```

Успешный ответ содержит как минимум:

```json
{
  "tokens": {
    "accessToken": "<JWT>",
    "refreshToken": "<refresh token>"
  }
  "terminalSessionResponse": "...",
  "acsAuthorizationResponse": "..."
}
```

Далее:

```http
Authorization: Bearer <accessToken>
```

### 3.2 Алгоритм HostTitle / HostIdent / Destination

- `HostTitle = USERDOMAIN\USERNAME@COMPUTERNAME`.
- `HostIdent = Base64(SHA512(UTF8(HostTitle)))`.
- `ApplicationCode = LarixLLC\Larix\Est\Manager`.
- `Destination` строится оригинальным `EncryptDecrypt.EncryptText(destination, HostIdent)`.
- Для AES используется CBC + PKCS7.
- Внутренний ключ: `Base64(SHA512(UTF8(HostIdent)))`, затем первые 24 символа.
- `IV = UTF-16LE(key[1:9])`.
- `AES key = UTF-16LE(key[8:24])`.
- Шифруется UTF-8 строка `http://localhost:5000/`, результат кодируется Base64.

## 4. Минимальный Python-шаблон

```python
import requests

BASE_URL = "http://localhost:5000"
s = requests.Session()

# 1) POST /auth с корректно сформированным terminalSessionRequest
# 2) token = response.json()['tokens']['accessToken']
# 3) s.headers['Authorization'] = f'Bearer {token}'
# 4) выполнять API-запросы через одну Session

r = s.get(f'{BASE_URL}/api/project/projects', timeout=30)
r.raise_for_status()
projects = r.json()
```

## 5. Практически важные цепочки

### Проверить, существует ли проект

1. `GET /api/project/projects`
2. Найти проект по `id`, `uniqueId` или `title`.

### Проверить, добавлены ли модели в проект

1. Получить `projectId`.
2. `GET /api/imcContainer/getProjectImcContainers/{projectId}`.
3. Если контейнеры существуют — проект содержит IMC-контейнеры/модели.
4. Для конкретного контейнера можно запросить `GET /api/imcSource/imcSources/{containerId}`.

### Проверить структуру

1. Получить `projectId`.
2. `GET /api/profile/getAllStructureProfile/{projectId}` + требуемый query-параметр типа профиля, если handler его требует.
3. Затем при необходимости `GET /api/profileItem/getAllStructureProfileItems/{id}`.

### Получить элементы модели

- `GET /api/imcElement/imcElements/{containerId}` — базовое получение элементов с query-параметрами handler'а.
- `POST /api/imcElement/getElementsByConditions/` — выборка по условиям.
- `POST /api/imcElement/getElementsBySelectors/` — выборка по selectors.

## 6. Полный каталог endpoint'ов

Всего восстановлено **271 HTTP endpoint'ов** и **1 SignalR hub**.

### AdministrationController

#### `GET /getApiVersion`

**Handler:** `GetApiVersion`  
**Назначение:** Получить версию Api  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `GetApiVersion`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:96`

#### `GET /getDataBaseVersion`

**Handler:** `GetDataBaseVersion`  
**Назначение:** Получить версию базы данных  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `GetDataBaseVersion`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:97`

#### `POST /auth`

**Handler:** `Auth`  
**Назначение:** Вход в систему  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `AuthRequest`  
**Request fields:** userAuthDto: UserAuthDto; terminalSessionRequest: TerminalSessionRequest  
**Response:** `200` → `AuthResponse`; `404` → `без тела`; `401` → `без тела`  
**Response fields:** AuthResponse => tokens: Tokens; terminalSessionResponse: TerminalSessionResponse; acsAuthorizationResponse: AcsBridgeCreateAuthorizationResponse  

**JSON skeleton запроса:**

```json
{
  "userAuthDto": {
    "login": "<string>",
    "password": "<string>"
  },
  "terminalSessionRequest": "<TerminalSessionRequest>"
}
```
**Endpoint name:** `Auth`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:74`

#### `POST /clearConditionsInProject/{projectId}`

**Handler:** `ClearConditionsInProject`  
**Назначение:** Назначение не документировано; по имени handler/route: `Clear Conditions In Project`.  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `projectId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `без тела`  
**Response fields:** —  
**Endpoint name:** `ClearConditionsInProject`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:98`

#### `POST /clearDatabase`

**Handler:** `ClearDatabase`  
**Назначение:** Очистить базу данных  
**Авторизация / ACS:** Bearer JWT required; ACS route must be configured as a hole or metadata inherited  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `ClearDatabase`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:90`

#### `POST /dropSession`

**Handler:** `DropSession`  
**Назначение:** Назначение не документировано; по имени handler/route: `Drop Session`.  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `TerminalSessionResponse`  
**Request fields:** —  
**Response:** `404` → `без тела`; `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
"<TerminalSessionResponse>"
```
**Endpoint name:** `DropSession`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:79`

#### `POST /queue`

**Handler:** `AddTaskToQueue`  
**Назначение:** Назначение не документировано; по имени handler/route: `Add Task To Queue`.  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `TaskQueue`  
**Request fields:** id: long; parentId: long?; rootParentId: long?; taskType: string; requestBody: string?; externalResponse: string?; status: string?; percent: int; startTs: DateTime?; finishTs: DateTime?; queueTs: DateTime; userId: long?; errorDetails: string?  
**Response:** `200` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "parentId": 0,
  "rootParentId": 0,
  "taskType": "<string>",
  "requestBody": "<string>",
  "externalResponse": "<string>",
  "status": "<string>",
  "percent": 0,
  "startTs": "<string>",
  "finishTs": "<string>",
  "queueTs": "<string>",
  "userId": 0,
  "errorDetails": "<string>"
}
```
**Endpoint name:** `TestQueueTask`  
**Tags:** `Queue`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:93`

#### `POST /refresh`

**Handler:** `Refresh`  
**Назначение:** Обновление JWT токенов  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `TokenDto`  
**Request fields:** accessToken: string?; refreshToken: string?  
**Response:** `200` → `TokenDto`; `404` → `без тела`; `401` → `без тела`  
**Response fields:** TokenDto => accessToken: string?; refreshToken: string?  

**JSON skeleton запроса:**

```json
{
  "accessToken": "<string>",
  "refreshToken": "<string>"
}
```
**Endpoint name:** `RefreshToken`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:83`

#### `POST /test`

**Handler:** `Test`  
**Назначение:** Тестовая отправка уведомлений  
**Авторизация / ACS:** Bearer JWT required; ACS route must be configured as a hole or metadata inherited  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** `message: string`  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `Test`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:91`

#### `POST /testTask`

**Handler:** `TestTask`  
**Назначение:** Назначение не документировано; по имени handler/route: `Test Task`.  
**Авторизация / ACS:** Bearer JWT required; ACS route must be configured as a hole or metadata inherited  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `TestTask`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:92`

#### `POST /uploadData`

**Handler:** `UploadData`  
**Назначение:** Загрузка ворсктореджа  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Stream`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
"<Stream>"
```
**Endpoint name:** `UploadWorkStorage`  
**Tags:** `Auth`  
**Источник:** `EST.WebApi.Controllers/AdministrationController.cs:88`

### CdbContainerController

#### `GET /api/cdbContainer/getContainer/{projectId}`

**Handler:** `GetCdbContainer`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Cdb Container`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Component`  
**Response fields:** Component => id: long; uniqueId: Guid?; parentId: long?; projectId: long?; solutionId: long?; componentType: ProjectComponentType; content: JsonDocument?; title: string?; isEnabled: bool?; description: string?; tags: JsonDocument?; createTs: DateTime; createUserId: long; updateTs: DateTime?; updateUserId: long?; attributes: JsonDocument?  
**Endpoint name:** `GetCdbContainer`  
**Tags:** `CdbContainer`  
**Источник:** `EST.WebApi.Controllers.Cdb/CdbContainerController.cs:29`

### CheckupController

#### `DELETE /api/checkup/deleteCollisionCheck/{profileItemId}`

**Handler:** `DeleteCollisionCheck`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Collision Check`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `без тела`  
**Response fields:** —  
**Endpoint name:** `DeleteCollisionCheck`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:62`

#### `GET /api/checkup/checkResultExist/{profileItemId}`

**Handler:** `CheckResultExist`  
**Назначение:** Назначение не документировано; по имени handler/route: `Check Result Exist`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `bool`; `401` → `без тела`  
**Response fields:** —  
**Endpoint name:** `CheckResultExist`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:50`

#### `GET /api/checkup/checkTheProfileItemForBeingInTheQueue/{profileItemId}`

**Handler:** `CheckTheProfileItemForBeingInTheQueue`  
**Назначение:** Проверяет находится ли <see cref="T:EST.WebApi.Models.DbModels.Profile.ProfileItem" /> в очереди на проверку  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileItemId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `bool`; `401` → `без тела`  
**Response fields:** —  
**Endpoint name:** `CheckTheProfileItemForBeingInTheQueue`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:45`

#### `GET /api/checkup/getCollisionResults/{profileItemId}`

**Handler:** `GetCollisionResults`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Collision Results`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `CollisionResult[]`  
**Response fields:** CollisionResult[] => id: long; collisionCheckId: long; elementId1: long; elementId2: long?; element1: ImcElement; element2: ImcElement?; meshes: byte[]?; meshVolumes: JsonDocument?; aaBoundingBoxes: JsonDocument?; aaVolumes: JsonDocument?; oBoundingBoxes: JsonDocument?; obbVolumes: JsonDocument?; status: CollisionStatus; priority: CollisionPriority; comment: string?; createTs: DateTime; updateTs: DateTime?; updateUserId: long?; distance: double?; counter: int  
**Endpoint name:** `GetResult`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:40`

#### `GET /api/checkup/getCollisionResultsByProfileIds/{projectId}`

**Handler:** `GetCollisionResultsByProfileIds`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Collision Results By Profile Ids`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileItemIds: long[]`, `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `CollisionResult[]`  
**Response fields:** CollisionResult[] => id: long; collisionCheckId: long; elementId1: long; elementId2: long?; element1: ImcElement; element2: ImcElement?; meshes: byte[]?; meshVolumes: JsonDocument?; aaBoundingBoxes: JsonDocument?; aaVolumes: JsonDocument?; oBoundingBoxes: JsonDocument?; obbVolumes: JsonDocument?; status: CollisionStatus; priority: CollisionPriority; comment: string?; createTs: DateTime; updateTs: DateTime?; updateUserId: long?; distance: double?; counter: int  
**Endpoint name:** `GetCollisionResultsByProfileIds`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:48`

#### `GET /api/checkup/getCollisionStatistics/{profileItemId}`

**Handler:** `GetCollisionStatistics`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Collision Statistics`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `CollisionStatistics[]`  
**Response fields:** CollisionStatistics[] => id: long; collisionCheckId: long; detectedCount: int; activeCount: int; fixedCount: int; createTs: DateTime  
**Endpoint name:** `GetStatistics`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:60`

#### `GET /api/checkup/getProfileItemsInTheQueue/{profileId}`

**Handler:** `GetProfileItemsInTheQueue`  
**Назначение:** Проверяет находится ли <see cref="T:EST.WebApi.Models.DbModels.Profile.ProfileItem" /> в очереди на проверку  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `long[]`; `401` → `без тела`  
**Response fields:** —  
**Endpoint name:** `GetProfileItemsInTheQueue`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:64`

#### `GET /api/checkup/getStatus/{profileItemId}`

**Handler:** `GetStatus`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Status`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `string`; `401` → `без тела`  
**Response fields:** —  
**Endpoint name:** `GetStatus`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:31`

#### `POST /api/checkup/cancel`

**Handler:** `CancelCheckupCollisions`  
**Назначение:** Отмена проверки на коллизии  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `collision_calculation`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `CheckupCollisionsRequest`  
**Request fields:** profileItemId: long; profileId: long; containerIds: long[]?  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "profileItemId": 0,
  "profileId": 0,
  "containerIds": [
    0
  ]
}
```
**Endpoint name:** `Cancel`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:37`

#### `POST /api/checkup/collision`

**Handler:** `CheckupCollisions`  
**Назначение:** Запрос проверки на коллизии  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `collision_calculation`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `CheckupCollisionsRequest`  
**Request fields:** profileItemId: long; profileId: long; containerIds: long[]?  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "profileItemId": 0,
  "profileId": 0,
  "containerIds": [
    0
  ]
}
```
**Endpoint name:** `Collision`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:34`

#### `POST /api/checkup/startCollisionValidationProfile`

**Handler:** `StartCollisionValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Start Collision Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `collision_calculation`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileCheckupRequest`  
**Request fields:** projectId: long; profileId: long; containerIds: long[]  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "projectId": 0,
  "profileId": 0,
  "containerIds": [
    0
  ]
}
```
**Endpoint name:** `StartCollisionValidationProfile`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:57`

#### `POST /api/checkup/updateCollisionResult`

**Handler:** `UpdateCollisionResult`  
**Назначение:** Назначение не документировано; по имени handler/route: `Update Collision Result`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `UpdateCollisionResultRequest`  
**Request fields:** collisionResultId: long; priority: CollisionPriority; comment: string?  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "collisionResultId": 0,
  "priority": "<CollisionPriority>",
  "comment": "<string>"
}
```
**Endpoint name:** `UpdateCollisionResult`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:42`

#### `POST /api/checkup/updateCollisionResultComments/{projectId}`

**Handler:** `UpdateCollisionResultComments`  
**Назначение:** Назначение не документировано; по имени handler/route: `Update Collision Result Comments`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `projectId: long`  
**Query:** —  
**Request body:** `UpdateCollisionResultCommentsRequest`  
**Request fields:** collisionResultIds: long[]; comment: string  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "collisionResultIds": [
    0
  ],
  "comment": "<string>"
}
```
**Endpoint name:** `UpdateCollisionResultComments`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:55`

#### `POST /api/checkup/updateCollisionResultPriorities/{projectId}`

**Handler:** `UpdateCollisionResultPriorities`  
**Назначение:** Назначение не документировано; по имени handler/route: `Update Collision Result Priorities`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `projectId: long`  
**Query:** —  
**Request body:** `UpdateCollisionResultPrioritiesRequest`  
**Request fields:** collisionResultIds: long[]; priority: CollisionPriority  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "collisionResultIds": [
    0
  ],
  "priority": "<CollisionPriority>"
}
```
**Endpoint name:** `UpdateCollisionResultPriorities`  
**Tags:** `Checkup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CheckupController.cs:53`

### CollisionReportExportController

#### `POST /api/checkup/export/{projectId}`

**Handler:** `ExportToExcel`  
**Назначение:** Получить отчет по коллизиям формата .xlsx в виде Stream  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** `projectId: long`  
**Query:** —  
**Request body:** `CollisionReportRequest`  
**Request fields:** profileId: long; containerIds: long[]; reportTypeIsBI: bool; collisionTypeReportDatas: CollisionTypeReportData[]  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "profileId": 0,
  "containerIds": [
    0
  ],
  "reportTypeIsBI": false,
  "collisionTypeReportDatas": [
    "<CollisionTypeReportData>"
  ]
}
```
**Endpoint name:** `Export`  
**Tags:** `Export`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CollisionReportExportController.cs:25`

#### `POST /api/checkup/getCollisionReportResultWithImageCount/{projectId}`

**Handler:** `GetCollisionReportResultWithImageCount`  
**Назначение:** Получить количество результатов проверки параметров  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** `projectId: long`  
**Query:** —  
**Request body:** `CollisionReportRequest`  
**Request fields:** profileId: long; containerIds: long[]; reportTypeIsBI: bool; collisionTypeReportDatas: CollisionTypeReportData[]  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "profileId": 0,
  "containerIds": [
    0
  ],
  "reportTypeIsBI": false,
  "collisionTypeReportDatas": [
    "<CollisionTypeReportData>"
  ]
}
```
**Endpoint name:** `GetCollisionReportResultWithImageCount`  
**Tags:** `Export`  
**Источник:** `EST.WebApi.Controllers.Checkup.Collisions/CollisionReportExportController.cs:27`

### ComponentController

#### `DELETE /api/component/component/{id}`

**Handler:** `DeleteComponent`  
**Назначение:** Удаление компонента  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteComponent`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:48`

#### `GET /api/component/component/getItemBySolutionAndType/{solutionId}`

**Handler:** `GetItemBySolutionAndType`  
**Назначение:** Получение компоненты по решению и типу  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** `componentType: short`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Component`  
**Response fields:** Component => id: long; uniqueId: Guid?; parentId: long?; projectId: long?; solutionId: long?; componentType: ProjectComponentType; content: JsonDocument?; title: string?; isEnabled: bool?; description: string?; tags: JsonDocument?; createTs: DateTime; createUserId: long; updateTs: DateTime?; updateUserId: long?; attributes: JsonDocument?  
**Endpoint name:** `GetComponentBySolutionAndType`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:33`

#### `GET /api/component/component/{id}`

**Handler:** `GetItem`  
**Назначение:** Получение компонента  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** `getContent: bool?`, `getTags: bool?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Component`  
**Response fields:** Component => id: long; uniqueId: Guid?; parentId: long?; projectId: long?; solutionId: long?; componentType: ProjectComponentType; content: JsonDocument?; title: string?; isEnabled: bool?; description: string?; tags: JsonDocument?; createTs: DateTime; createUserId: long; updateTs: DateTime?; updateUserId: long?; attributes: JsonDocument?  
**Endpoint name:** `GetComponent`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:31`

#### `GET /api/component/components/{projectId}`

**Handler:** `GetAllItems`  
**Назначение:** Получение списка компонент  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `type: short?`, `getContent: bool?`, `getTags: bool?`, `parentId: long?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Component[]`  
**Response fields:** Component[] => id: long; uniqueId: Guid?; parentId: long?; projectId: long?; solutionId: long?; componentType: ProjectComponentType; content: JsonDocument?; title: string?; isEnabled: bool?; description: string?; tags: JsonDocument?; createTs: DateTime; createUserId: long; updateTs: DateTime?; updateUserId: long?; attributes: JsonDocument?  
**Endpoint name:** `GetComponents`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:29`

#### `GET /api/component/getSolutionComponent/{projectId}`

**Handler:** `GetSolutionItem`  
**Назначение:** Получение компонента решения  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `solutionId: long`, `type: short?`, `getContent: bool?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Component`  
**Response fields:** Component => id: long; uniqueId: Guid?; parentId: long?; projectId: long?; solutionId: long?; componentType: ProjectComponentType; content: JsonDocument?; title: string?; isEnabled: bool?; description: string?; tags: JsonDocument?; createTs: DateTime; createUserId: long; updateTs: DateTime?; updateUserId: long?; attributes: JsonDocument?  
**Endpoint name:** `GetSolutionItem`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:35`

#### `POST /api/component/clearChainCodesFromStages/`

**Handler:** `ClearChainCodesFromStages`  
**Назначение:** Удаление GUID цепочки из стадий  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `SetStageDataRequest`  
**Request fields:** componentId: long; guids: string[]?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "componentId": 0,
  "guids": [
    "<string>"
  ]
}
```
**Endpoint name:** `ClearChainCodesFromStages`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:53`

#### `POST /api/component/component`

**Handler:** `PostComponent`  
**Назначение:** Создание компонента  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Component`  
**Request fields:** id: long; uniqueId: Guid?; parentId: long?; projectId: long?; solutionId: long?; componentType: ProjectComponentType; content: JsonDocument?; title: string?; isEnabled: bool?; description: string?; tags: JsonDocument?; createTs: DateTime; createUserId: long; updateTs: DateTime?; updateUserId: long?; attributes: JsonDocument?  
**Response:** `201` → `Component`  
**Response fields:** Component => id: long; uniqueId: Guid?; parentId: long?; projectId: long?; solutionId: long?; componentType: ProjectComponentType; content: JsonDocument?; title: string?; isEnabled: bool?; description: string?; tags: JsonDocument?; createTs: DateTime; createUserId: long; updateTs: DateTime?; updateUserId: long?; attributes: JsonDocument?  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "uniqueId": "<string>",
  "parentId": 0,
  "projectId": 0,
  "solutionId": 0,
  "componentType": 5,
  "content": {},
  "title": "<string>",
  "isEnabled": false,
  "description": "<string>",
  "tags": {},
  "createTs": "<string>",
  "createUserId": 0,
  "updateTs": "<string>",
  "updateUserId": 0,
  "attributes": {}
}
```
**Endpoint name:** `AddComponent`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:37`

#### `POST /api/component/getChainStatus/{componentId}`

**Handler:** `GetChainStatus`  
**Назначение:** Получение состояния цепочек по Id компонента  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** `componentId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ChainStatusDto[]`  
**Response fields:** ChainStatusDto[] => chainCode: string; isEnabled: bool  
**Endpoint name:** `GetChainStatus`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:49`

#### `POST /api/component/setComponentIsEnabled/{id}`

**Handler:** `SetIsEnabled`  
**Назначение:** Включение/выключение компонента  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `SetIsEnabledRequest`  
**Request fields:** isEnabled: bool  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "isEnabled": false
}
```
**Endpoint name:** `SetComponentIsEnabled`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:40`

#### `POST /api/component/setComponentTags/{id}`

**Handler:** `SetTags`  
**Назначение:** Обновление Tags компонента  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `SetTagsRequest`  
**Request fields:** tags: JsonDocument?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "tags": {}
}
```
**Endpoint name:** `SetTags`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:44`

#### `POST /api/component/setComponentTitleOrDescription/{id}`

**Handler:** `SetTitleOrDescription`  
**Назначение:** Обновление наименования/описания компонента  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `SetTitleDescriptionRequest`  
**Request fields:** title: string?; description: string?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "title": "<string>",
  "description": "<string>"
}
```
**Endpoint name:** `SetComponentTitleOrDescription`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:42`

#### `POST /api/component/setStageIsEnabled/`

**Handler:** `SetStageIsEnabled`  
**Назначение:** Включение/отключение стадии  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `SetStageIsEnabledRequest`  
**Request fields:** componentId: long; guids: string[]?; isEnabled: bool  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "componentId": 0,
  "guids": [
    "<string>"
  ],
  "isEnabled": false
}
```
**Endpoint name:** `SetStageIsEnabled`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:51`

#### `PUT /api/component/component`

**Handler:** `PutComponent`  
**Назначение:** Редактирование компонента  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Component`  
**Request fields:** id: long; uniqueId: Guid?; parentId: long?; projectId: long?; solutionId: long?; componentType: ProjectComponentType; content: JsonDocument?; title: string?; isEnabled: bool?; description: string?; tags: JsonDocument?; createTs: DateTime; createUserId: long; updateTs: DateTime?; updateUserId: long?; attributes: JsonDocument?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "uniqueId": "<string>",
  "parentId": 0,
  "projectId": 0,
  "solutionId": 0,
  "componentType": 5,
  "content": {},
  "title": "<string>",
  "isEnabled": false,
  "description": "<string>",
  "tags": {},
  "createTs": "<string>",
  "createUserId": 0,
  "updateTs": "<string>",
  "updateUserId": 0,
  "attributes": {}
}
```
**Endpoint name:** `UpdateComponent`  
**Tags:** `Component`  
**Источник:** `EST.WebApi.Controllers/ComponentController.cs:46`

### GlobalComponentController

#### `DELETE /api/globalComponent/globalComponent/{id}`

**Handler:** `DeleteGlobalComponent`  
**Назначение:** Удаление глобального компонента  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteGlobalComponent`  
**Tags:** `GlobalComponent`  
**Источник:** `EST.WebApi.Controllers/GlobalComponentController.cs:28`

#### `GET /api/globalComponent/globalComponent/{type}`

**Handler:** `GetItem`  
**Назначение:** Получение глобального компонента  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** Чтение / проверка  
**Path:** `type: short?`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `GlobalComponent`  
**Response fields:** GlobalComponent => id: long; componentType: GlobalComponentType?; content: JsonDocument?; updateTs: DateTime?; updateUserId: long?  
**Endpoint name:** `GetGlobalComponent`  
**Tags:** `GlobalComponent`  
**Источник:** `EST.WebApi.Controllers/GlobalComponentController.cs:21`

#### `POST /api/globalComponent/globalComponent`

**Handler:** `PostGlobalComponent`  
**Назначение:** Создание глобального компонента  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `GlobalComponent`  
**Request fields:** id: long; componentType: GlobalComponentType?; content: JsonDocument?; updateTs: DateTime?; updateUserId: long?  
**Response:** `201` → `GlobalComponent`  
**Response fields:** GlobalComponent => id: long; componentType: GlobalComponentType?; content: JsonDocument?; updateTs: DateTime?; updateUserId: long?  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "componentType": 1,
  "content": {},
  "updateTs": "<string>",
  "updateUserId": 0
}
```
**Endpoint name:** `AddGlobalComponent`  
**Tags:** `GlobalComponent`  
**Источник:** `EST.WebApi.Controllers/GlobalComponentController.cs:23`

#### `PUT /api/globalComponent/globalComponent`

**Handler:** `PutGlobalComponent`  
**Назначение:** Редактирование глобального компонента  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `GlobalComponent`  
**Request fields:** id: long; componentType: GlobalComponentType?; content: JsonDocument?; updateTs: DateTime?; updateUserId: long?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "componentType": 1,
  "content": {},
  "updateTs": "<string>",
  "updateUserId": 0
}
```
**Endpoint name:** `UpdateGlobalComponent`  
**Tags:** `GlobalComponent`  
**Источник:** `EST.WebApi.Controllers/GlobalComponentController.cs:26`

### ImcAdapterQueueController

#### `GET /api/imcAdapterQueue/getAdapterQueue/{containerId}`

**Handler:** `GetAdapterQueue`  
**Назначение:** Получение списка ImcAdapterQueue  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ GET, но по имени может запускать действие  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ImcAdapterQueue[]`  
**Response fields:** ImcAdapterQueue[] => id: long; index: int?; adapterId: long?; containerId: long?; title: string?  
**Endpoint name:** `GetAdapterQueue`  
**Tags:** `ImcAdapterQueue`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcAdapterQueueController.cs:21`

#### `POST /api/imcAdapterQueue/setAdapterQueue/{containerId}`

**Handler:** `SetAdapterQueue`  
**Назначение:** Установка очереди адаптеров в контейнере  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `adaptation`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `containerId: long`  
**Query:** `adapterIds: long[]?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ImcContainer[]`  
**Response fields:** ImcContainer[] => id: long; projectId: long?; solutionId: long?; uniqueId: Guid?; title: string?; attributes: JsonDocument?; offset: JsonDocument?; isEnabled: bool?; description: string?; updateTs: DateTime?; updateUserId: long?; receiveId: long?; extractorStartTs: DateTime?; extractorFinishTs: DateTime?; extractorStatus: ImcExtractStatus?; extractorLog: string?; sourceType: BimSourceType?; adapterStatus: ImcAdaptationStatus?; version: int; isVisible: bool; updateGeometryTs: DateTime?; adapterLog: string?; adapterHash: string?  
**Endpoint name:** `SetAdapterQueue`  
**Tags:** `ImcAdapterQueue`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcAdapterQueueController.cs:23`

### ImcContainerController

#### `DELETE /api/imcContainer/imcContainer/{containerId}`

**Handler:** `DeleteImcContainer`  
**Назначение:** Удаление IMC контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteImcContainer`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:55`

#### `GET /api/imcContainer/getAdaptationRelevance/{containerId}`

**Handler:** `GetAdaptationRelevance`  
**Назначение:** Получение признака актуальности модели  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** ⚠️ GET, но по имени может запускать действие  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `bool`  
**Response fields:** —  
**Endpoint name:** `GetAdaptationRelevance`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:64`

#### `GET /api/imcContainer/getImcContainerForSolution/{projectId}`

**Handler:** `GetImcContainerForSolutionAsync`  
**Назначение:** Получение IMC контейнера решения  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** `solutionId: long`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `EST.WebApi.Models.DbModels.Imc.ImcContainer`  
**Response fields:** EST.WebApi.Models.DbModels.Imc.ImcContainer => id: long; projectId: long?; solutionId: long?; uniqueId: Guid?; title: string?; attributes: JsonDocument?; offset: JsonDocument?; isEnabled: bool?; description: string?; updateTs: DateTime?; updateUserId: long?; receiveId: long?; extractorStartTs: DateTime?; extractorFinishTs: DateTime?; extractorStatus: ImcExtractStatus?; extractorLog: string?; sourceType: BimSourceType?; adapterStatus: ImcAdaptationStatus?; version: int; isVisible: bool; updateGeometryTs: DateTime?; adapterLog: string?; adapterHash: string?  
**Endpoint name:** `GetImcContainerForSolution`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:51`

#### `GET /api/imcContainer/getImcContainerIsEnabled/{containerId}`

**Handler:** `GetImcContainerIsEnabled`  
**Назначение:** Включение/выключение контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `bool`  
**Response fields:** —  
**Endpoint name:** `GetImcContainerIsEnabled`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:60`

#### `GET /api/imcContainer/getImcContainerParamValues/`

**Handler:** `GetImcContainerParamValues`  
**Назначение:** Получение списка уникальных значений параметров в рамках контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** `containerIds: long[]`, `paramDefinitionCode: string`, `parameterLayer: ParameterLayer?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `string[]`  
**Response fields:** —  
**Endpoint name:** `GetImcContainerParamValues`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:56`

#### `GET /api/imcContainer/getProjectImcContainers/{projectId}`

**Handler:** `GetProjectImcContainers`  
**Назначение:** Получение IMC контейнеров проекта  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `EST.WebApi.Models.DbModels.Imc.ImcContainer[]`  
**Response fields:** EST.WebApi.Models.DbModels.Imc.ImcContainer[] => id: long; projectId: long?; solutionId: long?; uniqueId: Guid?; title: string?; attributes: JsonDocument?; offset: JsonDocument?; isEnabled: bool?; description: string?; updateTs: DateTime?; updateUserId: long?; receiveId: long?; extractorStartTs: DateTime?; extractorFinishTs: DateTime?; extractorStatus: ImcExtractStatus?; extractorLog: string?; sourceType: BimSourceType?; adapterStatus: ImcAdaptationStatus?; version: int; isVisible: bool; updateGeometryTs: DateTime?; adapterLog: string?; adapterHash: string?  
**Endpoint name:** `GetProjectImcContainers`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:47`

#### `GET /api/imcContainer/imcContainer/{containerId}`

**Handler:** `GetImcContainerAsync`  
**Назначение:** Получение IMC контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `EST.WebApi.Models.DbModels.Imc.ImcContainer`  
**Response fields:** EST.WebApi.Models.DbModels.Imc.ImcContainer => id: long; projectId: long?; solutionId: long?; uniqueId: Guid?; title: string?; attributes: JsonDocument?; offset: JsonDocument?; isEnabled: bool?; description: string?; updateTs: DateTime?; updateUserId: long?; receiveId: long?; extractorStartTs: DateTime?; extractorFinishTs: DateTime?; extractorStatus: ImcExtractStatus?; extractorLog: string?; sourceType: BimSourceType?; adapterStatus: ImcAdaptationStatus?; version: int; isVisible: bool; updateGeometryTs: DateTime?; adapterLog: string?; adapterHash: string?  
**Endpoint name:** `GetImcContainer`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:53`

#### `GET /api/imcContainer/runAdaptation/{containerId}`

**Handler:** `RunModelAdaptation`  
**Назначение:** Запустить процесс адаптации модели  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `adaptation`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `bool`  
**Response fields:** —  
**Endpoint name:** `RunModelAdaptation`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:62`

#### `POST /api/imcContainer/exportImc/`

**Handler:** `ExportImc`  
**Назначение:** Назначение не документировано; по имени handler/route: `Export Imc`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `export`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `ImcExportRequest`  
**Request fields:** projectId: long; containerIds: long[]  
**Response:** `200` → `Stream`, application/octet-stream  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "projectId": 0,
  "containerIds": [
    0
  ]
}
```
**Endpoint name:** `ExportImc`  
**Tags:** `Export`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:66`

#### `POST /api/imcContainer/getChangedValues/`

**Handler:** `GetParameterValuesReport`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Parameter Values Report`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `ParameterValuesRequest`  
**Request fields:** projectId: long; containerIds: long[]; applicationName: string; container: string  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "projectId": 0,
  "containerIds": [
    0
  ],
  "applicationName": "<string>",
  "container": "<string>"
}
```
**Endpoint name:** `GetParameterValuesReport`  
**Tags:** `Export`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:69`

#### `POST /api/imcContainer/setImcContainerIsEnabled/{containerId}`

**Handler:** `SetImcContainerIsEnabled`  
**Назначение:** Включение/выключение контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `chain_use`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `SetIsEnabledRequest`  
**Request fields:** isEnabled: bool  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "isEnabled": false
}
```
**Endpoint name:** `SetImcContainerIsEnabled`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:58`

#### `POST /api/imcContainer/setImcContainerTitle/{containerId}`

**Handler:** `SetImcContainerTitle`  
**Назначение:** Изменение заголовка контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `SetTitleRequest`  
**Request fields:** title: string?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "title": "<string>"
}
```
**Endpoint name:** `SetImcContainerTitle`  
**Tags:** `ImcContainer`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcContainerController.cs:49`

### ImcElementController

#### `GET /api/imcElement/getElementsCount/{containerId}`

**Handler:** `GetElementsCount`  
**Назначение:** Получение количества элементов по Id контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `int`  
**Response fields:** —  
**Endpoint name:** `GetElementsCount`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:55`

#### `GET /api/imcElement/getImcElementsBySource/`

**Handler:** `GetImcElementsBySource`  
**Назначение:** Получение списка элементов по Id источникам  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** `sourceId: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ImcElement[]`  
**Response fields:** ImcElement[] => id: long; containerId: long; sourceId: long?; title: string?; uniqueId: string?; nativeId: string?; transformation: byte[]?; grefId: long?; onReceiveId: long?  
**Endpoint name:** `GetImcElementsBySource`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:42`

#### `GET /api/imcElement/getValidationResults/{profileItemId}`

**Handler:** `GetValidationResults`  
**Назначение:** Получение результата проверки параметров  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ValidationParameterErrorDto[]`  
**Response fields:** ValidationParameterErrorDto => elementId: long; elementNativeId: string; parameterId: long?; parameterCode: string?; parameterIsNumeric: bool?; parameterValueId: long?; parameterStringValue: string?; parameterNumericValue: decimal?  
**Endpoint name:** `GetValidationResults`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:62`

#### `GET /api/imcElement/imcElement/{id}`

**Handler:** `GetImcElement`  
**Назначение:** Получение элемета по Id  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ImcElement`  
**Response fields:** ImcElement => id: long; containerId: long; sourceId: long?; title: string?; uniqueId: string?; nativeId: string?; transformation: byte[]?; grefId: long?; onReceiveId: long?  
**Endpoint name:** `GetImcElement`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:44`

#### `GET /api/imcElement/imcElements/{containerId}`

**Handler:** `GetImcElements`  
**Назначение:** Получение списка элементов  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `containerId: long`  
**Query:** `filter: string?`, `paramIds: long[]?`, `filterParamIds: long[]?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ImcElement[]`  
**Response fields:** ImcElement[] => id: long; containerId: long; sourceId: long?; title: string?; uniqueId: string?; nativeId: string?; transformation: byte[]?; grefId: long?; onReceiveId: long?  
**Endpoint name:** `GetImcElements`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:40`

#### `POST /api/imcElement/deleteElements/`

**Handler:** `DeleteImcElements`  
**Назначение:** Удаляет элементы из контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `DeleteImcElementsRequest`  
**Request fields:** elementsWithContainerIds: ElementsWithContainerId[]  
**Response:** `200` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "elementsWithContainerIds": [
    "<ElementsWithContainerId>"
  ]
}
```
**Endpoint name:** `DeleteImcElements`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:57`

#### `POST /api/imcElement/getElementsByConditions/`

**Handler:** `GetElementsByConditions`  
**Назначение:** Получение списка элементов по списку идентификаторов  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `GetElementsByConditionsRequest`  
**Request fields:** containerIds: long[]?; sourceIds: long[]?; filter: string?; conditionBlock: ConditionsBlock?; availableElementIds: long[]?; availableElementGuids: string[]?; hooks: ParameterDefinitionHook[]  
**Response:** `200` → `ExpandoObject[]`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerIds": [
    0
  ],
  "sourceIds": [
    0
  ],
  "filter": "<string>",
  "conditionBlock": "<ConditionsBlock>",
  "availableElementIds": [
    0
  ],
  "availableElementGuids": [
    "<string>"
  ],
  "hooks": [
    "<ParameterDefinitionHook>"
  ]
}
```
**Endpoint name:** `GetElementsByConditions`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:46`

#### `POST /api/imcElement/getElementsByConditionsStream/`

**Handler:** `GetElementsByConditionsStream`  
**Назначение:** Получение списка элементов по списку идентификаторов  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `GetElementsByConditionsRequest`  
**Request fields:** containerIds: long[]?; sourceIds: long[]?; filter: string?; conditionBlock: ConditionsBlock?; availableElementIds: long[]?; availableElementGuids: string[]?; hooks: ParameterDefinitionHook[]  
**Response:** `200` → `ExpandoObject[]`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerIds": [
    0
  ],
  "sourceIds": [
    0
  ],
  "filter": "<string>",
  "conditionBlock": "<ConditionsBlock>",
  "availableElementIds": [
    0
  ],
  "availableElementGuids": [
    "<string>"
  ],
  "hooks": [
    "<ParameterDefinitionHook>"
  ]
}
```
**Endpoint name:** `GetElementsByConditionsStream`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:49`

#### `POST /api/imcElement/getElementsByProfileItem/`

**Handler:** `GetElementByProfileItem`  
**Назначение:** Получение списка элементов по Profile Item  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `GetElementByProfileItemRequest`  
**Request fields:** projectId: long; getElements: bool; getGrefs: bool; containerIds: long[]; profileItemId: long?; getElements1: bool; getElements2: bool; includeParentConditions: bool; includeChildConditions: bool; includeToElementsGroupingFields: bool; loadDetails: bool  
**Response:** `200` → `ExpandoObject[]`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "projectId": 0,
  "getElements": false,
  "getGrefs": false,
  "containerIds": [
    0
  ],
  "profileItemId": 0,
  "getElements1": false,
  "getElements2": false,
  "includeParentConditions": false,
  "includeChildConditions": false,
  "includeToElementsGroupingFields": false,
  "loadDetails": false
}
```
**Endpoint name:** `GetElementsByProfileItem2`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:60`

#### `POST /api/imcElement/getElementsBySelectors/`

**Handler:** `GetElementsBySelectors`  
**Назначение:** Получение списка элементов по списку идентификаторов  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `GetElementsBySelectorsRequest`  
**Request fields:** containerIds: long[]?; filter: string?; columnParamDefinitionIds: long[]?; availableElementIds: long[]?; elementUniqueIds: string[]?; sourceIds: long?[]?  
**Response:** `200` → `ExpandoObject[]`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerIds": [
    0
  ],
  "filter": "<string>",
  "columnParamDefinitionIds": [
    0
  ],
  "availableElementIds": [
    0
  ],
  "elementUniqueIds": [
    "<string>"
  ],
  "sourceIds": [
    0
  ]
}
```
**Endpoint name:** `GetElementsBySelectors`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:52`

#### `POST /api/imcElement/getElementsByStructure/`

**Handler:** `GetElementsByStructure`  
**Назначение:** Получение элементов по структуре и Profile Item  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `GetElementsByStructureRequest`  
**Request fields:** projectId: long; getElements: bool; getGrefs: bool; containerIds: long[]; profileItemId: long?; getElements1: bool; getElements2: bool; includeParentConditions: bool; includeChildConditions: bool; includeToElementsGroupingFields: bool; loadDetails: bool; filterSequence: List<StructureFilter>  
**Response:** `200` → `ExpandoObject[]`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "projectId": 0,
  "getElements": false,
  "getGrefs": false,
  "containerIds": [
    0
  ],
  "profileItemId": 0,
  "getElements1": false,
  "getElements2": false,
  "includeParentConditions": false,
  "includeChildConditions": false,
  "includeToElementsGroupingFields": false,
  "loadDetails": false,
  "filterSequence": [
    "<StructureFilter>"
  ]
}
```
**Endpoint name:** `GetElementsByStructure`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:66`

#### `POST /api/imcElement/getStructure/`

**Handler:** `GetStructure`  
**Назначение:** Получение структуры по Profile Item  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `GetElementByProfileItemRequest`  
**Request fields:** projectId: long; getElements: bool; getGrefs: bool; containerIds: long[]; profileItemId: long?; getElements1: bool; getElements2: bool; includeParentConditions: bool; includeChildConditions: bool; includeToElementsGroupingFields: bool; loadDetails: bool  
**Response:** `200` → `TreeItemDto`  
**Response fields:** TreeItemDto => title: string; children: List<TreeItemDto>  

**JSON skeleton запроса:**

```json
{
  "projectId": 0,
  "getElements": false,
  "getGrefs": false,
  "containerIds": [
    0
  ],
  "profileItemId": 0,
  "getElements1": false,
  "getElements2": false,
  "includeParentConditions": false,
  "includeChildConditions": false,
  "includeToElementsGroupingFields": false,
  "loadDetails": false
}
```
**Endpoint name:** `GetStructure`  
**Tags:** `ImcElement`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:64`

#### `POST /api/profileElementMap/getElementsByProfileElements`

**Handler:** `GetElementsByProfileElements`  
**Назначение:** Получить элементы по profile Id и percent как ExpandoObjects  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `GetStatusesRequest`  
**Request fields:** profileItemId: long; percents: int[]?  
**Response:** `200` → `ExpandoObject[]`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "profileItemId": 0,
  "percents": [
    0
  ]
}
```
**Endpoint name:** `GetElementsByProfileElements`  
**Tags:** `ProfileElementMap`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcElementController.cs:68`

### ImcGrefController

#### `DELETE /api/imcSource/clearSourcesGeometry/{containerId}`

**Handler:** `ClearSourcesGeometry`  
**Назначение:** Удаление геометрии по источникам  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `containerId: long`  
**Query:** `sourceIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `без тела`  
**Response fields:** —  
**Endpoint name:** `ClearSourcesGeometry`  
**Tags:** `ImcGref`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcGrefController.cs:30`

#### `POST /api/imcGref/deleteElementsGeometry/`

**Handler:** `DeleteElementsGeometry`  
**Назначение:** Удаление геометрии эллементов из контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `DeleteElementsGeometryRequest`  
**Request fields:** elementsWithContainerIds: ElementsWithContainerId[]  
**Response:** `200` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "elementsWithContainerIds": [
    "<ElementsWithContainerId>"
  ]
}
```
**Endpoint name:** `DeleteElementsGeometry`  
**Tags:** `ImcGref`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcGrefController.cs:27`

#### `POST /api/imcGref/getImcGref/{containerId}`

**Handler:** `GetGeometry`  
**Назначение:** Получение списка ImcGref  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `GetImcElementGeometryRequest`  
**Request fields:** take: int; skip: int; elementIds: long[]?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "take": 0,
  "skip": 0,
  "elementIds": [
    0
  ]
}
```
**Endpoint name:** `GetGeometry`  
**Tags:** `ImcGref`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcGrefController.cs:21`

#### `POST /api/imcGref/getSourceImcGref/{containerId}`

**Handler:** `GetSourcesGeometry`  
**Назначение:** Получение списка ImcGref  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `GetImcSourceGeometryRequest`  
**Request fields:** take: int; skip: int; sourceIds: long[]?  
**Response:** `200` → `ImcGref[]`  
**Response fields:** ImcGref[] => id: long; containerId: long?; geometry: byte[]?; elementId: long  

**JSON skeleton запроса:**

```json
{
  "take": 0,
  "skip": 0,
  "sourceIds": [
    0
  ]
}
```
**Endpoint name:** `GetSourcesGeometry`  
**Tags:** `ImcGref`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcGrefController.cs:24`

#### `POST /api/imcSource/getHasGeometry/`

**Handler:** `GetHasGeometry`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Has Geometry`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `GetImcHasGeometryRequest`  
**Request fields:** containerIds: long[]?  
**Response:** `200` → `bool`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerIds": [
    0
  ]
}
```
**Endpoint name:** `GetHasGeometry`  
**Tags:** `ImcGref`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcGrefController.cs:32`

### ImcParameterDefinitionController

#### `GET /api/imcParameterDefinition/getImcParameterDefinitionCount/{containerId}`

**Handler:** `GetImcParameterDefinitionCountAsync`  
**Назначение:** Получение количества параметров  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `containerId: long`  
**Query:** `parameterLayer: ParameterLayer?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `int`  
**Response fields:** —  
**Endpoint name:** `GetImcParameterDefinitionCountAsync`  
**Tags:** `ImcParameterDefinition`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterDefinitionController.cs:33`

#### `GET /api/imcParameterDefinition/getParameterLayers`

**Handler:** `GetParameterLayers`  
**Назначение:** Получение списка слоев для контейнеров  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `short[]`  
**Response fields:** —  
**Endpoint name:** `GetParameterLayers`  
**Tags:** `ImcParameterDefinition`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterDefinitionController.cs:37`

#### `GET /api/imcParameterDefinition/imcParameterDefinitions/`

**Handler:** `GetImcParamDefinitions`  
**Назначение:** Получение списка параметров  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** `containerIds: long[]`, `filter: string?`, `parameterLayer: ParameterLayer?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ImcParameterDefinition[]`  
**Response fields:** ImcParameterDefinition[] => id: long; containerId: long; title: string?; isNumeric: bool; layer: short?; description: string?; code: string?; dataTypeNativeName: string?; uom: string?; unitType: string?; reportColumnType: short?  
**Endpoint name:** `GetImcParamDefinitions`  
**Tags:** `ImcParameterDefinition`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterDefinitionController.cs:27`

#### `POST /api/imcParameterDefinition/deleteImcParamDefinitions/`

**Handler:** `DeleteImcParamDefinitions`  
**Назначение:** Удаляет параметры из контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `SetImcParameterDefinitionRequest`  
**Request fields:** containerIds: long[]; parameterCodes: string[]; parameterLayer: ParameterLayer?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerIds": [
    0
  ],
  "parameterCodes": [
    "<string>"
  ],
  "parameterLayer": "<ParameterLayer>"
}
```
**Endpoint name:** `DeleteImcParamDefinitions`  
**Tags:** `ImcParameterDefinition`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterDefinitionController.cs:29`

#### `POST /api/imcParameterDefinition/imcParameterDefinition/`

**Handler:** `CreateParameterDefinition`  
**Назначение:** Создание параметра  
**Авторизация / ACS:** Access token required; ACS permission check (no [Authorize] attribute); ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `CreateImcParameterDefinitionRequest`  
**Request fields:** elementMaps: ElementMap[]; code: string; isNumeric: bool; uom: string?; numericValue: decimal?; stringValue: string?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "elementMaps": [
    "<ElementMap>"
  ],
  "code": "<string>",
  "isNumeric": false,
  "uom": "<string>",
  "numericValue": 0,
  "stringValue": "<string>"
}
```
**Endpoint name:** `CreateParameterDefinition`  
**Tags:** `ImcParameterDefinition`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterDefinitionController.cs:35`

#### `POST /api/imcParameterDefinition/resetAlternateValue/`

**Handler:** `ResetAlternateValue`  
**Назначение:** Удаляет параметры из контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `SetImcParameterDefinitionRequest`  
**Request fields:** containerIds: long[]; parameterCodes: string[]; parameterLayer: ParameterLayer?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerIds": [
    0
  ],
  "parameterCodes": [
    "<string>"
  ],
  "parameterLayer": "<ParameterLayer>"
}
```
**Endpoint name:** `ResetAlternateValueAsync`  
**Tags:** `ImcParameterDefinition`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterDefinitionController.cs:31`

### ImcParameterValueController

#### `GET /api/imcParameterValue/getImcParameterValuesCount/{containerId}`

**Handler:** `GetImcParameterValuesCount`  
**Назначение:** Получение количества значений параметров  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `containerId: long`  
**Query:** `elementId: long`, `parameterLayer: ParameterLayer?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `int`  
**Response fields:** —  
**Endpoint name:** `GetImcParameterValuesCount`  
**Tags:** `ImcParameterValue`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterValueController.cs:25`

#### `GET /api/imcParameterValue/imcParameterValues/{elementId}`

**Handler:** `GetImcParameterValues`  
**Назначение:** Получение списка значений параметров элемента  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `elementId: long`  
**Query:** `filter: string?`, `parameterLayer: ParameterLayer?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ImcParameterValue[]`  
**Response fields:** ImcParameterValue[] => id: long; elementId: long; containerId: long; parameterDefinitionId: long; originValueNumeric: decimal?; alternativeValueNumeric: decimal?; originValueString: string?; alternativeValueString: string?; onAlternative: bool?; code: string?; isNumeric: bool; layer: short?; sourceInfo: AttributeSourceInfo  
**Endpoint name:** `GetImcParameterValues`  
**Tags:** `ImcParameterValue`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterValueController.cs:23`

#### `POST /api/imcParameterValue/clearAlternateValueByElements/`

**Handler:** `ClearAlternateValueByElements`  
**Назначение:** Очистка альтернативных значений у элементов  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ClearParamAlternateValueByElementsRequest`  
**Request fields:** containerId: long; elementIds: long[]  
**Response:** `200` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerId": 0,
  "elementIds": [
    0
  ]
}
```
**Endpoint name:** `ClearAlternateValueByElements`  
**Tags:** `ImcParameterValue`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterValueController.cs:30`

#### `POST /api/imcParameterValue/clearAlternateValueBySources/`

**Handler:** `ClearAlternateValueBySources`  
**Назначение:** Очистка альтернативных значений у элементов  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ClearParamAlternateValueBySourcesRequest`  
**Request fields:** containerId: long; sourceIds: long[]?  
**Response:** `200` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerId": 0,
  "sourceIds": [
    0
  ]
}
```
**Endpoint name:** `ClearAlternateValueBySources`  
**Tags:** `ImcParameterValue`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterValueController.cs:27`

#### `POST /api/imcParameterValue/setAlternateValueByElements/`

**Handler:** `SetAlternateValueByElements`  
**Назначение:** Установка альтернативных значений у элементов  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `SetParamAlternateValueByElementsRequest`  
**Request fields:** containerIds: ElementsWithContainerId[]; parameterCode: string; isNumeric: bool; numericValue: decimal?; stringValue: string?  
**Response:** `200` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerIds": [
    "<ElementsWithContainerId>"
  ],
  "parameterCode": "<string>",
  "isNumeric": false,
  "numericValue": 0,
  "stringValue": "<string>"
}
```
**Endpoint name:** `SetAlternateValueByElements`  
**Tags:** `ImcParameterValue`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterValueController.cs:36`

#### `POST /api/imcParameterValue/setAlternateValueBySources/`

**Handler:** `SetAlternateValueBySources`  
**Назначение:** Установка альтернативных значений у элементов  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `SetParamAlternateValueBySourcesRequest`  
**Request fields:** containerId: long; parameterCode: string; sourceIds: long[]?; isNumeric: bool; numericValue: decimal?; stringValue: string?  
**Response:** `200` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "containerId": 0,
  "parameterCode": "<string>",
  "sourceIds": [
    0
  ],
  "isNumeric": false,
  "numericValue": 0,
  "stringValue": "<string>"
}
```
**Endpoint name:** `SetAlternateValueBySources`  
**Tags:** `ImcParameterValue`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcParameterValueController.cs:33`

### ImcSourceController

#### `DELETE /api/imcSource/imcSource/{containerId}`

**Handler:** `DeleteSources`  
**Назначение:** Удаление источников контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `containerId: long`  
**Query:** `sourceIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `без тела`  
**Response fields:** —  
**Endpoint name:** `DeleteSources`  
**Tags:** `ImcSource`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcSourceController.cs:23`

#### `GET /api/imcSource/imcSources/{containerId}`

**Handler:** `GetAllItems`  
**Назначение:** Получение списка IMC источников  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ImcSourceDto[]`  
**Response fields:** ImcSourceDto[] => id: long; value: string?; containerId: long; elementCount: int; geometryCount: int  
**Endpoint name:** `GetImcSources`  
**Tags:** `ImcSource`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcSourceController.cs:18`

#### `POST /api/imcSource/updateSources/{containerId}`

**Handler:** `UpdateSources`  
**Назначение:** Обновление источников контейнера  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `containerId: long`  
**Query:** —  
**Request body:** `UpdateImcSourceRequest`  
**Request fields:** sourceIds: long[]; newValue: string  
**Response:** `200` → `ImcSourceDto[]`  
**Response fields:** ImcSourceDto[] => id: long; value: string?; containerId: long; elementCount: int; geometryCount: int  

**JSON skeleton запроса:**

```json
{
  "sourceIds": [
    0
  ],
  "newValue": "<string>"
}
```
**Endpoint name:** `UpdateSources`  
**Tags:** `ImcSource`  
**Источник:** `EST.WebApi.Controllers.Imc/ImcSourceController.cs:20`

### LicensureController

#### `GET /api/larixlicenseactivator/getOpenerRequest/{licenseKey}`

**Handler:** `GetOpenerRequest`  
**Назначение:** Получить LicenseActivatorResponse в ответ на ключ лицензии  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** Чтение / проверка  
**Path:** `licenseKey: string`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `RecipientLicenseActivatorResponse`  
**Response fields:** —  
**Endpoint name:** `GetOpenerRequest`  
**Tags:** `Licensure`  
**Источник:** `EST.WebApi.Controllers/LicensureController.cs:29`

#### `GET /api/larixlicenseactivator/getStatus`

**Handler:** `GetStatus`  
**Назначение:** Запросить статус активации  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ActivationStatus`  
**Response fields:** —  
**Endpoint name:** `GetLicenseStatus`  
**Tags:** `Licensure`  
**Источник:** `EST.WebApi.Controllers/LicensureController.cs:20`

#### `GET RecipientLicenseActivatorPaths.GetLicensePeriod`

**Handler:** `GetLicensePeriod`  
**Назначение:** Запросить сведения о периоде действия лицензии  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `LicensePeriod`  
**Response fields:** —  
**Endpoint name:** `GetLicensePeriod`  
**Tags:** `Licensure`  
**Источник:** `EST.WebApi.Controllers/LicensureController.cs:23`

#### `GET RecipientLicenseActivatorPaths.MethodHello ?? ""`

**Handler:** `Hello`  
**Назначение:** Проверить соединение с хостом  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `Ping`  
**Tags:** `Licensure`  
**Источник:** `EST.WebApi.Controllers/LicensureController.cs:34`

#### `POST /api/larixlicenseactivator/reset`

**Handler:** `Reset`  
**Назначение:** Выполнить сброс активации  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `string`  
**Request fields:** JSON string  
**Response:** `200` → `RecipientLicenseActivatorResponse`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
"<string>"
```
**Endpoint name:** `Reset`  
**Tags:** `Licensure`  
**Источник:** `EST.WebApi.Controllers/LicensureController.cs:26`

#### `POST /api/larixlicenseactivator/sendOpenerResponse`

**Handler:** `SetOpenerResponse`  
**Назначение:** Завершить активацию  
**Авторизация / ACS:** No JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `string`  
**Request fields:** JSON string  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
"<string>"
```
**Endpoint name:** `SetOpenerResponse`  
**Tags:** `Licensure`  
**Источник:** `EST.WebApi.Controllers/LicensureController.cs:32`

### ParametersCheckupController

#### `DELETE /api/parametersCheckup/deleteValidationParameter/{id}`

**Handler:** `DeleteValidationParameter`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Validation Parameter`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteValidationParameter`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:47`

#### `DELETE /api/parametersCheckup/deleteValidationParameters/`

**Handler:** `DeleteValidationParameters`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Validation Parameters`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** `validationParameterIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteValidationParameters`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:48`

#### `GET /api/parametersCheckup/checkParameterValidationExist/{profileItemId}`

**Handler:** `CheckParameterValidationExist`  
**Назначение:** Проверяет существует ли запись о постановке на проверку параметров  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `bool`; `401` → `без тела`  
**Response fields:** —  
**Endpoint name:** `CheckParameterValidationExist`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:56`

#### `GET /api/parametersCheckup/checkResultExist/{profileItemId}`

**Handler:** `CheckResultExist`  
**Назначение:** Назначение не документировано; по имени handler/route: `Check Result Exist`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `bool`; `401` → `без тела`  
**Response fields:** —  
**Endpoint name:** `CheckParameterResultExist`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:53`

#### `GET /api/parametersCheckup/getLibraryValidationParameters`

**Handler:** `GetLibraryValidationParameters`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Library Validation Parameters`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ValidationParameter[]`  
**Response fields:** ValidationParameter[] => id: long; profileId: long?; code: string; isNumeric: bool; acceptableValueRules: string?; comment: string?  
**Endpoint name:** `GetLibraryValidationParameters`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:35`

#### `GET /api/parametersCheckup/getProfileItemsWhereCheckExists/{profileId}`

**Handler:** `GetProfileItemsWhereCheckExists`  
**Назначение:** Возвращает список profileItem'ов, по которым была проведена проверка  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `long[]`; `401` → `без тела`  
**Response fields:** —  
**Endpoint name:** `GetProfileItemsWhereCheckExists`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:62`

#### `GET /api/parametersCheckup/getProfileItemsWhereResultExists/{profileId}`

**Handler:** `GetProfileItemsWhereResultExists`  
**Назначение:** Возвращает список profileItem'ов, у которых есть результаты проверки  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `long[]`; `401` → `без тела`  
**Response fields:** —  
**Endpoint name:** `GetProfileItemsWhereResultExists`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:65`

#### `GET /api/parametersCheckup/getValidationParameters/{profileId}`

**Handler:** `GetValidationParameters`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Validation Parameters`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ValidationParameter[]`  
**Response fields:** ValidationParameter[] => id: long; profileId: long?; code: string; isNumeric: bool; acceptableValueRules: string?; comment: string?  
**Endpoint name:** `GetValidationParameters`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:33`

#### `GET /api/parametersCheckup/parameter/{profileItemId}`

**Handler:** `GetCheckupResult`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Checkup Result`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `401` → `ValidationParameterErrorDto[]`  
**Response fields:** ValidationParameterErrorDto => elementId: long; elementNativeId: string; parameterId: long?; parameterCode: string?; parameterIsNumeric: bool?; parameterValueId: long?; parameterStringValue: string?; parameterNumericValue: decimal?  
**Endpoint name:** `GetCheckupResult`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:51`

#### `POST /api/checkup/startParameterValidationProfile`

**Handler:** `StartParameterValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Start Parameter Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `check_start`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileCheckupRequest`  
**Request fields:** projectId: long; profileId: long; containerIds: long[]  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "projectId": 0,
  "profileId": 0,
  "containerIds": [
    0
  ]
}
```
**Endpoint name:** `StartParameterValidationProfile`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:59`

#### `POST /api/parametersCheckup/parameter/{profileItemId}`

**Handler:** `CheckupParameters`  
**Назначение:** Назначение не документировано; по имени handler/route: `Checkup Parameters`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `check_start`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** `profileItemId: long`  
**Query:** `containerIds: long[]`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `401` → `без тела`  
**Response fields:** —  
**Endpoint name:** `GetCheckupParameters`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:49`

#### `POST /api/parametersCheckup/postValidationParameter`

**Handler:** `PostValidationParameter`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Validation Parameter`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ValidationParameter`  
**Request fields:** id: long; profileId: long?; code: string; isNumeric: bool; acceptableValueRules: string?; comment: string?  
**Response:** `201` → `ValidationParameter`  
**Response fields:** ValidationParameter => id: long; profileId: long?; code: string; isNumeric: bool; acceptableValueRules: string?; comment: string?  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "code": "<string>",
  "isNumeric": false,
  "acceptableValueRules": "<string>",
  "comment": "<string>"
}
```
**Endpoint name:** `PostValidationParameter`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:37`

#### `POST /api/parametersCheckup/postValidationParameters`

**Handler:** `PostValidationParameters`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Validation Parameters`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ValidationParameter[]`  
**Request fields:** id: long; profileId: long?; code: string; isNumeric: bool; acceptableValueRules: string?; comment: string?  
**Response:** `201` → `ValidationParameter[]`  
**Response fields:** ValidationParameter[] => id: long; profileId: long?; code: string; isNumeric: bool; acceptableValueRules: string?; comment: string?  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "code": "<string>",
    "isNumeric": false,
    "acceptableValueRules": "<string>",
    "comment": "<string>"
  }
]
```
**Endpoint name:** `PostValidationParameters`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:40`

#### `PUT /api/parametersCheckup/putValidationParameter`

**Handler:** `PutValidationParameter`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Validation Parameter`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ValidationParameter`  
**Request fields:** id: long; profileId: long?; code: string; isNumeric: bool; acceptableValueRules: string?; comment: string?  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "code": "<string>",
  "isNumeric": false,
  "acceptableValueRules": "<string>",
  "comment": "<string>"
}
```
**Endpoint name:** `PutValidationParameter`  
**Tags:** `ParametersCheckup`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersCheckupController.cs:43`

### ParametersReportExportController

#### `POST api/parametersCheckup/getReport/`

**Handler:** `GetReport`  
**Назначение:** Получить отчет по параметрам формата .xlsx в виде Stream  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** `projectId: long`  
**Request body:** `ValidationReportRequest`  
**Request fields:** profileId: long; containerIds: long[]; reportTypeIsBI: bool; addAttributeSourceInfo: bool; datas: ParameterValidationTypeReportData[]  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "profileId": 0,
  "containerIds": [
    0
  ],
  "reportTypeIsBI": false,
  "addAttributeSourceInfo": false,
  "datas": [
    "<ParameterValidationTypeReportData>"
  ]
}
```
**Endpoint name:** `GetParametersReport`  
**Tags:** `Export`  
**Источник:** `EST.WebApi.Controllers.Checkup.Parameters/ParametersReportExportController.cs:19`

### ProfileController

#### `DELETE /api/profile/deleteCollisionBIReportProfile/{id}`

**Handler:** `DeleteCollisionBIReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Collision BIReport Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteCollisionBIReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:149`

#### `DELETE /api/profile/deleteCollisionReportProfile/{id}`

**Handler:** `DeleteCollisionReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Collision Report Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteCollisionReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:148`

#### `DELETE /api/profile/deleteCollisionValidationProfile/{id}`

**Handler:** `DeleteCollisionValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Collision Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteCollisionValidationProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:147`

#### `DELETE /api/profile/deleteListProfile/{id}`

**Handler:** `DeleteListProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete List Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteListProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:145`

#### `DELETE /api/profile/deleteModelProfile/{id}`

**Handler:** `DeleteModelProfile`  
**Назначение:** Удаление профиля  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteModelProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:140`

#### `DELETE /api/profile/deleteParameterValidationBIReportProfile/{id}`

**Handler:** `DeleteParameterValidationBIReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Parameter Validation BIReport Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteParameterValidationBIReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:151`

#### `DELETE /api/profile/deleteParameterValidationProfile/{id}`

**Handler:** `DeleteParameterValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Parameter Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteParameterValidationProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:146`

#### `DELETE /api/profile/deleteParameterValidationReportProfile/{id}`

**Handler:** `DeleteParameterValidationReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Parameter Validation Report Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteParameterValidationReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:150`

#### `DELETE /api/profile/deleteSetProfile/{id}`

**Handler:** `DeleteSetProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Set Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteSetProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:142`

#### `DELETE /api/profile/deleteStatusProfile/{id}`

**Handler:** `DeleteStatusProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Status Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteStatusProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:143`

#### `DELETE /api/profile/deleteStructureProfile/{id}`

**Handler:** `DeleteStructureProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Structure Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteStructureProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:141`

#### `DELETE /api/profile/deleteViewProfile/{id}`

**Handler:** `DeleteViewProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete View Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteViewProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:144`

#### `GET /api/profile/getAllCollisionBIReportProfile/{projectId}`

**Handler:** `GetAllCollisionBIReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Collision BIReport Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllCollisionBIReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:50`

#### `GET /api/profile/getAllCollisionReportProfile/{projectId}`

**Handler:** `GetAllCollisionReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Collision Report Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllCollisionReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:48`

#### `GET /api/profile/getAllCollisionValidationProfile/{projectId}`

**Handler:** `GetAllCollisionValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Collision Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllCollisionValidationProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:46`

#### `GET /api/profile/getAllListProfile/{projectId}`

**Handler:** `GetAllListProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All List Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllListProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:42`

#### `GET /api/profile/getAllModelProfile/{projectId}`

**Handler:** `GetAllModelProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Model Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllModelProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:32`

#### `GET /api/profile/getAllParameterValidationBIReportProfile/{projectId}`

**Handler:** `GetAllParameterValidationBIReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Parameter Validation BIReport Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllParameterValidationBIReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:54`

#### `GET /api/profile/getAllParameterValidationProfile/{projectId}`

**Handler:** `GetAllParameterValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Parameter Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllParameterValidationProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:44`

#### `GET /api/profile/getAllParameterValidationReportProfile/{projectId}`

**Handler:** `GetAllParameterValidationReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Parameter Validation Report Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllParameterValidationReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:52`

#### `GET /api/profile/getAllSetProfile/{projectId}`

**Handler:** `GetAllSetProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Set Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllSetProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:36`

#### `GET /api/profile/getAllStatusProfile/{projectId}`

**Handler:** `GetAllStatusProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Status Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllStatusProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:38`

#### `GET /api/profile/getAllStructureProfile/{projectId}`

**Handler:** `GetAllStructureProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Structure Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllStructureProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:34`

#### `GET /api/profile/getAllViewProfile/{projectId}`

**Handler:** `GetAllViewProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All View Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `profileType: ProfileType`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Profile[]`  
**Response fields:** Profile[] => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Endpoint name:** `GetAllViewProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:40`

#### `POST /api/profile/`

**Handler:** `ConvertProfile`  
**Назначение:** конвертация профиля набора в профиль проверки параметров  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `profile_change`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `ConvertProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:152`

#### `POST /api/profile/postCollisionBIReportProfile`

**Handler:** `PostCollisionBIReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Collision BIReport Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostCollisionBIReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:83`

#### `POST /api/profile/postCollisionReportProfile`

**Handler:** `PostCollisionReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Collision Report Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostCollisionReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:80`

#### `POST /api/profile/postCollisionValidationProfile`

**Handler:** `PostCollisionValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Collision Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostCollisionValidationProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:77`

#### `POST /api/profile/postListProfile`

**Handler:** `PostListProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post List Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostListProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:71`

#### `POST /api/profile/postModelProfile`

**Handler:** `PostModelProfile`  
**Назначение:** Создание профиля  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostModelProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:56`

#### `POST /api/profile/postParameterValidationBIReportProfile`

**Handler:** `PostParameterValidationBIReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Parameter Validation BIReport Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostParameterValidationBIReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:89`

#### `POST /api/profile/postParameterValidationProfile`

**Handler:** `PostParameterValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Parameter Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostParameterValidationProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:74`

#### `POST /api/profile/postParameterValidationReportProfile`

**Handler:** `PostParameterValidationReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Parameter Validation Report Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostParameterValidationReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:86`

#### `POST /api/profile/postSetProfile`

**Handler:** `PostSetProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Set Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostSetProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:62`

#### `POST /api/profile/postStatusProfile`

**Handler:** `PostStatusProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Status Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostStatusProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:65`

#### `POST /api/profile/postStructureProfile`

**Handler:** `PostStructureProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Structure Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostStructureProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:59`

#### `POST /api/profile/postViewProfile`

**Handler:** `PostViewProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post View Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `201` → `Profile`  
**Response fields:** Profile => id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PostViewProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:68`

#### `PUT /api/profile/putCollisionBIReportProfile`

**Handler:** `PutCollisionBIReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Collision BIReport Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutCollisionBIReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:128`

#### `PUT /api/profile/putCollisionReportProfile`

**Handler:** `PutCollisionReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Collision Report Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutCollisionReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:124`

#### `PUT /api/profile/putCollisionValidationProfile`

**Handler:** `PutCollisionValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Collision Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutCollisionValidationProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:120`

#### `PUT /api/profile/putListProfile`

**Handler:** `PutListProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put List Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutListProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:112`

#### `PUT /api/profile/putModelProfile`

**Handler:** `PutModelProfile`  
**Назначение:** Редактирование проекта  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutModelProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:92`

#### `PUT /api/profile/putParameterValidationBIReportProfile`

**Handler:** `PutParameterValidationBIReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Parameter Validation BIReport Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutParameterValidationBIReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:136`

#### `PUT /api/profile/putParameterValidationProfile`

**Handler:** `PutParameterValidationProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Parameter Validation Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutParameterValidationProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:116`

#### `PUT /api/profile/putParameterValidationReportProfile`

**Handler:** `PutParameterValidationReportProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Parameter Validation Report Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutParameterValidationReportProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:132`

#### `PUT /api/profile/putSetProfile`

**Handler:** `PutSetProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Set Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutSetProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:100`

#### `PUT /api/profile/putStatusProfile`

**Handler:** `PutStatusProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Status Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutStatusProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:104`

#### `PUT /api/profile/putStructureProfile`

**Handler:** `PutStructureProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Structure Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutStructureProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:96`

#### `PUT /api/profile/putViewProfile`

**Handler:** `PutViewProfile`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put View Profile`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `profile_change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Profile`  
**Request fields:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "projectId": 0,
  "title": "<string>",
  "comment": "<string>",
  "profileType": 0
}
```
**Endpoint name:** `PutViewProfile`  
**Tags:** `Profile`  
**Источник:** `EST.WebApi.Controllers/ProfileController.cs:108`

### ProfileElementMapController

#### `DELETE /api/profileElementMap/deleteProfileElementMapsFromProfile`

**Handler:** `DeleteProfileElementMapsFromProfile`  
**Назначение:** Удаляет существующие Profile Element Maps  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** `profileId: long`  
**Request body:** `string[]`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  "<string>"
]
```
**Endpoint name:** `DeleteProfileElementMapsFromProfile`  
**Tags:** `ProfileElementMap`  
**Источник:** `EST.WebApi.Controllers/ProfileElementMapController.cs:37`

#### `GET /api/profileElementMap/profileElement/profile/{profileId}`

**Handler:** `GetProfileElementMapByProfile`  
**Назначение:** Получить Profile Element Map по профилю  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `profileId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileElementMap[]`  
**Response fields:** ProfileElementMap[] => id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  
**Endpoint name:** `GetProfileElementMapByProfile`  
**Tags:** `ProfileElementMap`  
**Источник:** `EST.WebApi.Controllers/ProfileElementMapController.cs:23`

#### `GET /api/profileElementMap/profileElement/status/{statusId}`

**Handler:** `GetProfileElementMapByStatus`  
**Назначение:** Получить Profile Element Map по статусу  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `statusId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileElementMap[]`  
**Response fields:** ProfileElementMap[] => id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  
**Endpoint name:** `GetProfileElementMapByStatus`  
**Tags:** `ProfileElementMap`  
**Источник:** `EST.WebApi.Controllers/ProfileElementMapController.cs:21`

#### `GET /api/profileElementMap/profileElement/uid/{uniqueId}`

**Handler:** `GetProfileElementMapByUid`  
**Назначение:** Получить Profile Element Map по уникальному идентификатору  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `uniqueId: string`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileElementMap[]`  
**Response fields:** ProfileElementMap[] => id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  
**Endpoint name:** `GetProfileElementMapByUid`  
**Tags:** `ProfileElementMap`  
**Источник:** `EST.WebApi.Controllers/ProfileElementMapController.cs:25`

#### `GET /api/profileElementMap/profileElements/statusAndProfile`

**Handler:** `GetProfileElementsByStatusAndProfile`  
**Назначение:** Получить Profile Element Map по статусу и профилю  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** `statusId: long`, `profileId: long`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileElementMap[]`  
**Response fields:** ProfileElementMap[] => id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  
**Endpoint name:** `GetProfileElementsByStatusAndProfile`  
**Tags:** `ProfileElementMap`  
**Источник:** `EST.WebApi.Controllers/ProfileElementMapController.cs:27`

#### `GET /api/profileElementMap/profileElements/uidAndProfile/{uniqueId}`

**Handler:** `GetProfileElementsByUidAndProfile`  
**Назначение:** Получить Profile Element Map по уникальному идентификатору и профилю  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `uniqueId: string`  
**Query:** `profileId: long`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileElementMap[]`  
**Response fields:** ProfileElementMap[] => id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  
**Endpoint name:** `GetProfileElementsByUidAndProfile`  
**Tags:** `ProfileElementMap`  
**Источник:** `EST.WebApi.Controllers/ProfileElementMapController.cs:29`

#### `POST /api/profileElementMap/profileElementMap`

**Handler:** `PostProfileElementMap`  
**Назначение:** Добавить новый или обновить существующий Profile Element Map  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileElementMap`  
**Request fields:** id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  
**Response:** `201` → `ProfileElementMap`  
**Response fields:** ProfileElementMap => id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "containerId": 0,
  "profileItemId": 0,
  "elementUniqueId": "<string>",
  "date": "<string>",
  "percent": 0,
  "profileId": 0
}
```
**Endpoint name:** `AddProfileElementMap`  
**Tags:** `ProfileElementMap`  
**Источник:** `EST.WebApi.Controllers/ProfileElementMapController.cs:31`

#### `POST /api/profileElementMap/profileElementMaps`

**Handler:** `PostProfileElementMaps`  
**Назначение:** Добавить новый или обновить существующие Profile Element Maps  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileElementMap[]`  
**Request fields:** id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  
**Response:** `201` → `ProfileElementMap[]`  
**Response fields:** ProfileElementMap[] => id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "containerId": 0,
    "profileItemId": 0,
    "elementUniqueId": "<string>",
    "date": "<string>",
    "percent": 0,
    "profileId": 0
  }
]
```
**Endpoint name:** `AddProfileElementMaps`  
**Tags:** `ProfileElementMap`  
**Источник:** `EST.WebApi.Controllers/ProfileElementMapController.cs:34`

### ProfileItemController

#### `DELETE /api/profileItem/deleteCollisionBIReportProfileItem/{id}`

**Handler:** `DeleteCollisionBIReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Collision BIReport Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteCollisionBIReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:221`

#### `DELETE /api/profileItem/deleteCollisionReportProfileItem/{id}`

**Handler:** `DeleteCollisionReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Collision Report Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteCollisionReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:220`

#### `DELETE /api/profileItem/deleteCollisionValidationProfileItem/{id}`

**Handler:** `DeleteCollisionValidationProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Collision Validation Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteCollisionValidationProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:219`

#### `DELETE /api/profileItem/deleteListProfileItem/{id}`

**Handler:** `DeleteListProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete List Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteListProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:217`

#### `DELETE /api/profileItem/deleteModelProfileItem/{id}`

**Handler:** `DeleteModelProfileItem`  
**Назначение:** Удаление содержимого профиля  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteModelProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:212`

#### `DELETE /api/profileItem/deleteParameterValidationBIReportProfileItem/{id}`

**Handler:** `DeleteParameterValidationBIReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Parameter Validation BIReport Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteParameterValidationBIReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:223`

#### `DELETE /api/profileItem/deleteParameterValidationProfileItem/{id}`

**Handler:** `DeleteParameterValidationProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Parameter Validation Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteParameterValidationProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:218`

#### `DELETE /api/profileItem/deleteParameterValidationReportProfileItem/{id}`

**Handler:** `DeleteParameterValidationReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Parameter Validation Report Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteParameterValidationReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:222`

#### `DELETE /api/profileItem/deleteSetProfileItem/{id}`

**Handler:** `DeleteSetProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Set Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteSetProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:214`

#### `DELETE /api/profileItem/deleteStatusProfileItem/{id}`

**Handler:** `DeleteStatusProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Status Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteStatusProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:215`

#### `DELETE /api/profileItem/deleteStructureProfileItem/{id}`

**Handler:** `DeleteStructureProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete Structure Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteStructureProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:213`

#### `DELETE /api/profileItem/deleteViewProfileItem/{id}`

**Handler:** `DeleteViewProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Delete View Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteViewProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:216`

#### `GET /api/profileItem/getAllCollisionBIReportProfileItems/{id}`

**Handler:** `GetAllCollisionBIReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Collision BIReport Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllCollisionBIReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:44`

#### `GET /api/profileItem/getAllCollisionReportProfileItems/{id}`

**Handler:** `GetAllCollisionReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Collision Report Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllCollisionReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:42`

#### `GET /api/profileItem/getAllCollisionValidationProfileItems/{id}`

**Handler:** `GetAllCollisionValidationProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Collision Validation Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllCollisionValidationProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:40`

#### `GET /api/profileItem/getAllListProfileItems/{id}`

**Handler:** `GetAllListProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All List Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllListProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:36`

#### `GET /api/profileItem/getAllModelProfileItems/{id}`

**Handler:** `GetAllModelProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Model Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `models` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllModelProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:26`

#### `GET /api/profileItem/getAllParameterValidationBIReportProfileItems/{id}`

**Handler:** `GetAllParameterValidationBIReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Parameter Validation BIReport Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllParameterValidationBIReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:48`

#### `GET /api/profileItem/getAllParameterValidationProfileItems/{id}`

**Handler:** `GetAllParameterValidationProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Parameter Validation Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllParameterValidationProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:38`

#### `GET /api/profileItem/getAllParameterValidationReportProfileItems/{id}`

**Handler:** `GetAllParameterValidationReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Parameter Validation Report Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllParameterValidationReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:46`

#### `GET /api/profileItem/getAllSetProfileItems/{id}`

**Handler:** `GetAllSetProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Set Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllSetProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:30`

#### `GET /api/profileItem/getAllStatusProfileItems/{id}`

**Handler:** `GetAllStatusProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Status Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllStatusProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:32`

#### `GET /api/profileItem/getAllStructureProfileItems/{id}`

**Handler:** `GetAllStructureProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All Structure Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllStructureProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:28`

#### `GET /api/profileItem/getAllViewProfileItems/{id}`

**Handler:** `GetAllViewProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get All View Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem[]`  
**Response fields:** ProfileItem[] => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetAllViewProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:34`

#### `GET /api/profileItem/profileItem/{id}`

**Handler:** `GetProfileItem`  
**Назначение:** Получение элемента профиля  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** Чтение / проверка  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Endpoint name:** `GetProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:50`

#### `POST /api/profileItem/postCollisionBIReportProfileItem`

**Handler:** `PostCollisionBIReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Collision BIReport Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostCollisionBIReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:79`

#### `POST /api/profileItem/postCollisionReportProfileItem`

**Handler:** `PostCollisionReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Collision Report Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostCollisionReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:76`

#### `POST /api/profileItem/postCollisionValidationProfileItem`

**Handler:** `PostCollisionValidationProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Collision Validation Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostCollisionValidationProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:73`

#### `POST /api/profileItem/postListProfileItem`

**Handler:** `PostListProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post List Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostListProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:67`

#### `POST /api/profileItem/postModelProfileItem`

**Handler:** `PostModelProfileItem`  
**Назначение:** Создание содержимого профиля  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostModelProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:52`

#### `POST /api/profileItem/postParameterValidationBIReportProfileItem`

**Handler:** `PostParameterValidationBIReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Parameter Validation BIReport Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostParameterValidationBIReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:85`

#### `POST /api/profileItem/postParameterValidationProfileItem`

**Handler:** `PostParameterValidationProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Parameter Validation Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostParameterValidationProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:70`

#### `POST /api/profileItem/postParameterValidationReportProfileItem`

**Handler:** `PostParameterValidationReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Parameter Validation Report Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostParameterValidationReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:82`

#### `POST /api/profileItem/postSetProfileItem`

**Handler:** `PostSetProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Set Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostSetProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:58`

#### `POST /api/profileItem/postStatusProfileItem`

**Handler:** `PostStatusProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Status Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostStatusProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:61`

#### `POST /api/profileItem/postStructureProfileItem`

**Handler:** `PostStructureProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Structure Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostStructureProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:55`

#### `POST /api/profileItem/postViewProfileItem`

**Handler:** `PostViewProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post View Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `201` → `ProfileItem`  
**Response fields:** ProfileItem => id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PostViewProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:64`

#### `POST /api/profileItem/profileItem/postCollisionBIReportProfileItems`

**Handler:** `PostCollisionBIReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Collision BIReport Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostCollisionBIReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:115`

#### `POST /api/profileItem/profileItem/postCollisionReportProfileItems`

**Handler:** `PostCollisionReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Collision Report Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostCollisionReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:112`

#### `POST /api/profileItem/profileItem/postCollisionValidationProfileItems`

**Handler:** `PostCollisionValidationProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Collision Validation Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostCollisionValidationProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:109`

#### `POST /api/profileItem/profileItem/postListProfileItems`

**Handler:** `PostListProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post List Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostListProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:103`

#### `POST /api/profileItem/profileItem/postModelProfileItems`

**Handler:** `PostModelProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Model Profile Items`.  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostModelProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:88`

#### `POST /api/profileItem/profileItem/postParameterValidationBIReportProfileItems`

**Handler:** `PostParameterValidationBIReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Parameter Validation BIReport Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostParameterValidationBIReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:121`

#### `POST /api/profileItem/profileItem/postParameterValidationProfileItems`

**Handler:** `PostParameterValidationProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Parameter Validation Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostParameterValidationProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:106`

#### `POST /api/profileItem/profileItem/postParameterValidationReportProfileItems`

**Handler:** `PostParameterValidationReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Parameter Validation Report Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostParameterValidationReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:118`

#### `POST /api/profileItem/profileItem/postSetProfileItems`

**Handler:** `PostSetProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Set Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostSetProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:94`

#### `POST /api/profileItem/profileItem/postStatusProfileItems`

**Handler:** `PostStatusProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Status Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostStatusProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:97`

#### `POST /api/profileItem/profileItem/postStructureProfileItems`

**Handler:** `PostStructureProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post Structure Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostStructureProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:91`

#### `POST /api/profileItem/profileItem/postViewProfileItems`

**Handler:** `PostViewProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Post View Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PostViewProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:100`

#### `PUT /api/profileItem/profileItem/putCollisionBIReportProfileItems`

**Handler:** `PutCollisionBIReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Collision BIReport Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutCollisionBIReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:203`

#### `PUT /api/profileItem/profileItem/putCollisionReportProfileItems`

**Handler:** `PutCollisionReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Collision Report Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutCollisionReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:200`

#### `PUT /api/profileItem/profileItem/putCollisionValidationProfileItems`

**Handler:** `PutCollisionValidationProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Collision Validation Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutCollisionValidationProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:197`

#### `PUT /api/profileItem/profileItem/putListProfileItems`

**Handler:** `PutListProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put List Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutListProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:191`

#### `PUT /api/profileItem/profileItem/putModelProfileItems`

**Handler:** `PutModelProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Model Profile Items`.  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutModelProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:176`

#### `PUT /api/profileItem/profileItem/putParameterValidationBIReportProfileItems`

**Handler:** `PutParameterValidationBIReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Parameter Validation BIReport Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutParameterValidationBIReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:209`

#### `PUT /api/profileItem/profileItem/putParameterValidationProfileItems`

**Handler:** `PutParameterValidationProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Parameter Validation Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutParameterValidationProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:194`

#### `PUT /api/profileItem/profileItem/putParameterValidationReportProfileItems`

**Handler:** `PutParameterValidationReportProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Parameter Validation Report Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutParameterValidationReportProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:206`

#### `PUT /api/profileItem/profileItem/putSetProfileItems`

**Handler:** `PutSetProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Set Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutSetProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:182`

#### `PUT /api/profileItem/profileItem/putStatusProfileItems`

**Handler:** `PutStatusProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Status Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutStatusProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:185`

#### `PUT /api/profileItem/profileItem/putStructureProfileItems`

**Handler:** `PutStructureProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Structure Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutStructureProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:179`

#### `PUT /api/profileItem/profileItem/putViewProfileItems`

**Handler:** `PutViewProfileItems`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put View Profile Items`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem[]`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `401` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
[
  {
    "id": 0,
    "profileId": 0,
    "parentId": 0,
    "title": "<string>",
    "comment": "<string>",
    "type": 0,
    "containerId": 0,
    "isEnabled": false,
    "groupFieldParamCodes": {},
    "extFieldParamCodes": {},
    "condition1": "<ConditionData>",
    "condition2": "<ConditionData>",
    "condition1Id": 0,
    "condition2Id": 0,
    "parentCondition1Id": 0,
    "parentCondition2Id": 0,
    "elementGuids1": [
      "<string>"
    ],
    "elementGuids2": [
      "<string>"
    ],
    "parentElementGuids1Id": 0,
    "parentElementGuids2Id": 0,
    "color": {},
    "camera": {},
    "itemParams": {},
    "isFolder": false,
    "index": 0
  }
]
```
**Endpoint name:** `PutViewProfileItems`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:188`

#### `PUT /api/profileItem/profileItemIndexUpdate`

**Handler:** `ProfileItemIndexUpdate`  
**Назначение:** Назначение не документировано; по имени handler/route: `Profile Item Index Update`.  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItemIndexUpdateRequest`  
**Request fields:** profileId: long; map: ProfileItemIndexUpdateMap[]  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "profileId": 0,
  "map": [
    "<ProfileItemIndexUpdateMap>"
  ]
}
```
**Endpoint name:** `ProfileItemIndexUpdate`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:224`

#### `PUT /api/profileItem/putCollisionBIReportProfileItem`

**Handler:** `PutCollisionBIReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Collision BIReport Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutCollisionBIReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:164`

#### `PUT /api/profileItem/putCollisionReportProfileItem`

**Handler:** `PutCollisionReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Collision Report Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutCollisionReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:160`

#### `PUT /api/profileItem/putCollisionValidationProfileItem`

**Handler:** `PutCollisionValidationProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Collision Validation Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `collision_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutCollisionValidationProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:156`

#### `PUT /api/profileItem/putListProfileItem`

**Handler:** `PutListProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put List Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `lists` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutListProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:148`

#### `PUT /api/profileItem/putModelProfileItem`

**Handler:** `PutModelProfileItem`  
**Назначение:** Редактирование содержимого профиля  
**Авторизация / ACS:** Bearer JWT required; ACS bypass  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutModelProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:124`

#### `PUT /api/profileItem/putParameterValidationBIReportProfileItem`

**Handler:** `PutParameterValidationBIReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Parameter Validation BIReport Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutParameterValidationBIReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:172`

#### `PUT /api/profileItem/putParameterValidationProfileItem`

**Handler:** `PutParameterValidationProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Parameter Validation Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutParameterValidationProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:152`

#### `PUT /api/profileItem/putParameterValidationReportProfileItem`

**Handler:** `PutParameterValidationReportProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Parameter Validation Report Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `parameters_check` → `export`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutParameterValidationReportProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:168`

#### `PUT /api/profileItem/putSetProfileItem`

**Handler:** `PutSetProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Set Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutSetProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:132`

#### `PUT /api/profileItem/putStatusProfileItem`

**Handler:** `PutStatusProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Status Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutStatusProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:136`

#### `PUT /api/profileItem/putStructureProfileItem`

**Handler:** `PutStructureProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put Structure Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `column_sets` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutStructureProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:128`

#### `PUT /api/profileItem/putViewProfileItem`

**Handler:** `PutViewProfileItem`  
**Назначение:** Назначение не документировано; по имени handler/route: `Put View Profile Item`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `views` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProfileItem`  
**Request fields:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "profileId": 0,
  "parentId": 0,
  "title": "<string>",
  "comment": "<string>",
  "type": 0,
  "containerId": 0,
  "isEnabled": false,
  "groupFieldParamCodes": {},
  "extFieldParamCodes": {},
  "condition1": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition2": {
    "id": 0,
    "body": {},
    "hasElements": false,
    "isActual": false,
    "hash": "<string>",
    "projectId": 0
  },
  "condition1Id": 0,
  "condition2Id": 0,
  "parentCondition1Id": 0,
  "parentCondition2Id": 0,
  "elementGuids1": [
    "<string>"
  ],
  "elementGuids2": [
    "<string>"
  ],
  "parentElementGuids1Id": 0,
  "parentElementGuids2Id": 0,
  "color": {},
  "camera": {},
  "itemParams": {},
  "isFolder": false,
  "index": 0
}
```
**Endpoint name:** `PutViewProfileItem`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:144`

#### `PUT /api/profileItem/setStatusProfileItemIsEnabled`

**Handler:** `SetStatusProfileItemIsEnabled`  
**Назначение:** Назначение не документировано; по имени handler/route: `Set Status Profile Item Is Enabled`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `statuses` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `IsEnableProfileItemRequest`  
**Request fields:** profileItemId: long; isEnabled: bool  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "profileItemId": 0,
  "isEnabled": false
}
```
**Endpoint name:** `SetStatusProfileItemIsEnabled`  
**Tags:** `ProfileItem`  
**Источник:** `EST.WebApi.Controllers/ProfileItemController.cs:140`

### Program

#### `HUB notificationHub`

**Handler:** `—`  
**Назначение:** Назначение не документировано; по имени handler/route: `notification Hub`.  
**Авторизация / ACS:** SignalR hub; auth metadata not established from MapHub line  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Источник:** `Program.cs:85`

### ProjectController

#### `DELETE /api/project/projects/{id}`

**Handler:** `DeleteProject`  
**Назначение:** Удаление проекта  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `delete`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteProject`  
**Tags:** `Project`  
**Источник:** `EST.WebApi.Controllers/ProjectController.cs:62`

#### `GET /api/project/projects`

**Handler:** `GetAllItems`  
**Назначение:** Получение списка проектов  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** —  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Project[]`  
**Response fields:** Project[] => id: long; uniqueId: Guid?; title: string?; description: string?; createTs: DateTime; createUserId: long; user: User?; receiveId: long?; cdbSourceUniqueId: string?; cdbSourceTarget: CDBSourceTarget?; author: UserDto?  
**Endpoint name:** `GetProjects`  
**Tags:** `Project`  
**Источник:** `EST.WebApi.Controllers/ProjectController.cs:51`

#### `GET /api/project/projects/{id}`

**Handler:** `GetItem`  
**Назначение:** Получение проекта  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `id: long?`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Project`  
**Response fields:** Project => id: long; uniqueId: Guid?; title: string?; description: string?; createTs: DateTime; createUserId: long; user: User?; receiveId: long?; cdbSourceUniqueId: string?; cdbSourceTarget: CDBSourceTarget?; author: UserDto?  
**Endpoint name:** `GetProject`  
**Tags:** `Project`  
**Источник:** `EST.WebApi.Controllers/ProjectController.cs:53`

#### `POST /api/project/projects`

**Handler:** `PostProject`  
**Назначение:** Создание проекта  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Project`  
**Request fields:** id: long; uniqueId: Guid?; title: string?; description: string?; createTs: DateTime; createUserId: long; user: User?; receiveId: long?; cdbSourceUniqueId: string?; cdbSourceTarget: CDBSourceTarget?; author: UserDto?  
**Response:** `201` → `Project`  
**Response fields:** Project => id: long; uniqueId: Guid?; title: string?; description: string?; createTs: DateTime; createUserId: long; user: User?; receiveId: long?; cdbSourceUniqueId: string?; cdbSourceTarget: CDBSourceTarget?; author: UserDto?  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "uniqueId": "<string>",
  "title": "<string>",
  "description": "<string>",
  "createTs": "<string>",
  "createUserId": 0,
  "user": {
    "id": 0,
    "acsLogin": "<string>",
    "acsId": 0,
    "isDeleted": false
  },
  "receiveId": 0,
  "cdbSourceUniqueId": "<string>",
  "cdbSourceTarget": 0,
  "author": {
    "id": 0,
    "acsLogin": "<string>"
  }
}
```
**Endpoint name:** `AddProject`  
**Tags:** `Project`  
**Источник:** `EST.WebApi.Controllers/ProjectController.cs:55`

#### `POST /api/project/projects/startCalculation`

**Handler:** `StartProcessCalculation`  
**Назначение:** Выполнить расчет решения для заданного проекта  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `solution_calculation`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `ProcessCalculationRequest`  
**Request fields:** projectId: long; title: string; description: string  
**Response:** `200` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "projectId": 0,
  "title": "<string>",
  "description": "<string>"
}
```
**Endpoint name:** `StartProcessCalculation`  
**Tags:** `Project`  
**Источник:** `EST.WebApi.Controllers/ProjectController.cs:63`

#### `PUT /api/project/projects`

**Handler:** `PutProject`  
**Назначение:** Редактирование проекта  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `project` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Project`  
**Request fields:** id: long; uniqueId: Guid?; title: string?; description: string?; createTs: DateTime; createUserId: long; user: User?; receiveId: long?; cdbSourceUniqueId: string?; cdbSourceTarget: CDBSourceTarget?; author: UserDto?  
**Response:** `400` → `без тела`; `404` → `без тела`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "uniqueId": "<string>",
  "title": "<string>",
  "description": "<string>",
  "createTs": "<string>",
  "createUserId": 0,
  "user": {
    "id": 0,
    "acsLogin": "<string>",
    "acsId": 0,
    "isDeleted": false
  },
  "receiveId": 0,
  "cdbSourceUniqueId": "<string>",
  "cdbSourceTarget": 0,
  "author": {
    "id": 0,
    "acsLogin": "<string>"
  }
}
```
**Endpoint name:** `UpdateProject`  
**Tags:** `Project`  
**Источник:** `EST.WebApi.Controllers/ProjectController.cs:58`

### ReportController

#### `GET /api/report/checkCubeContainsColumns/{solutionId}`

**Handler:** `CheckCubeContainsColumns`  
**Назначение:** Назначение не документировано; по имени handler/route: `Check Cube Contains Columns`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions_reports` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `long`  
**Request fields:** —  
**Response:** `200` → `bool`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
0
```
**Endpoint name:** `CheckCubeContainsColumns`  
**Tags:** `Report`  
**Источник:** `EST.WebApi.Controllers/ReportController.cs:28`

#### `GET /api/report/checkCubeIsExist/{solutionId}`

**Handler:** `CheckCubeIsExist`  
**Назначение:** Назначение не документировано; по имени handler/route: `Check Cube Is Exist`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions_reports` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `bool`  
**Response fields:** —  
**Endpoint name:** `CheckCubeIsExist`  
**Tags:** `Report`  
**Источник:** `EST.WebApi.Controllers/ReportController.cs:26`

#### `GET /api/report/checkSolutionContainsColumns/{solutionId}`

**Handler:** `CheckSolutionContainsColumns`  
**Назначение:** Назначение не документировано; по имени handler/route: `Check Solution Contains Columns`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions_reports` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `long`  
**Request fields:** —  
**Response:** `200` → `bool`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
0
```
**Endpoint name:** `CheckSolutionContainsColumns`  
**Tags:** `Report`  
**Источник:** `EST.WebApi.Controllers/ReportController.cs:31`

#### `GET /api/report/checkSolutionHasCubeColumns/{solutionId}`

**Handler:** `CheckSolutionHasCubeColumns`  
**Назначение:** Назначение не документировано; по имени handler/route: `Check Solution Has Cube Columns`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions_reports` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `long`  
**Request fields:** —  
**Response:** `200` → `bool`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
0
```
**Endpoint name:** `CheckSolutionHasCubeColumns`  
**Tags:** `Report`  
**Источник:** `EST.WebApi.Controllers/ReportController.cs:34`

#### `POST /api/report/getComparisonReportData/`

**Handler:** `GetComparisonReportData`  
**Назначение:** Получение отчета по нескольким решениям  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions_reports` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `ReportRequest`  
**Request fields:** isReportMode: bool; customData: CustomDataGridJsonModel  
**Response:** `200` → `object[]`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "isReportMode": false,
  "customData": "<CustomDataGridJsonModel>"
}
```
**Endpoint name:** `GetComparisonReportData`  
**Tags:** `Report`  
**Источник:** `EST.WebApi.Controllers/ReportController.cs:23`

#### `POST /api/report/getReportData/{solutionId}`

**Handler:** `GetReportData`  
**Назначение:** Получение отчета  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions_reports` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `ReportRequest`  
**Request fields:** isReportMode: bool; customData: CustomDataGridJsonModel  
**Response:** `200` → `object[]`  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "isReportMode": false,
  "customData": "<CustomDataGridJsonModel>"
}
```
**Endpoint name:** `GetReportData`  
**Tags:** `Report`  
**Источник:** `EST.WebApi.Controllers/ReportController.cs:20`

### SolutionController

#### `DELETE /api/solution/solutions/{id}`

**Handler:** `DeleteSolution`  
**Назначение:** Удаление решения  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `DeleteSolution`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:33`

#### `GET /api/solution/getCdbObjectTypeHierarchy/{solutionId}`

**Handler:** `GetCdbObjectTypeHierarchy`  
**Назначение:** Получение списка иерархии типов CDB для решения  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `CdbObjectTypeHierarchyDto[]`  
**Response fields:** CdbObjectTypeHierarchyDto[] => objectTypeId: long; parentObjectTypeId: long?; level: int; maxDepth: int; title: string  
**Endpoint name:** `GetCdbObjectTypeHierarchy`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:43`

#### `GET /api/solution/getCdbWorksForElement/{solutionId}`

**Handler:** `GetCdbWorksForElement`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Cdb Works For Element`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** `elementId: long`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ElementHanlersTreeRowDto[]`  
**Response fields:** ElementHanlersTreeRowDto[] => nodeId: long; parentNodeId: long; cdbItemCode: string; cdbItemTitle: string; quantity: double; metrics: string  
**Endpoint name:** `GetCdbWorksForElement`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:41`

#### `GET /api/solution/getColumnValuesFromCube/{solutionId}`

**Handler:** `GetColumnValuesFromCube`  
**Назначение:** Получение списка значений колонки из куба  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** `columnHash: string`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `string[]`  
**Response fields:** —  
**Endpoint name:** `GetColumnValuesFromCubeAsync`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:45`

#### `GET /api/solution/getElementActionMap/{solutionId}`

**Handler:** `GetElementActionMap`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Element Action Map`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `ElementActionMapDto[]`  
**Response fields:** ElementActionMapDto[] => elementId: long; actionCount: int; workCount: int  
**Endpoint name:** `GetElementActionMap`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:37`

#### `GET /api/solution/getElementWithoutWorkCount/{solutionId}`

**Handler:** `GetElementWithoutWorkCount`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Element Without Work Count`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `int`  
**Response fields:** —  
**Endpoint name:** `GetElementWithoutWorkCount`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:39`

#### `GET /api/solution/getTransactions/{solutionId}`

**Handler:** `GetTransactions`  
**Назначение:** Запрос транзакций по идентификатору решения  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `SolutionAceqTransaction[]`  
**Response fields:** SolutionAceqTransaction[] => id: long; solutionId: int; handlerActionId: int; cdbNodeId: int; elementId: long; activityCode: string; quantity: double; expenditure: double; indicatorValues: double[]?; transition: JsonDocument  
**Endpoint name:** `GetTransactions`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:35`

#### `GET /api/solution/solutions/{projectId}`

**Handler:** `GetAllItems`  
**Назначение:** Получение списка решений  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Чтение / проверка  
**Path:** `projectId: long`  
**Query:** `id: long?`  
**Request body:** `—`  
**Request fields:** —  
**Response:** `200` → `Solution[]`  
**Response fields:** Solution[] => id: long; uniqueId: Guid?; projectId: long?; title: string?; description: string?; createUserId: long; createTs: DateTime; processorStartTs: DateTime?; processorFinishTs: DateTime?; processorStatus: ProcessorStatus; processorLog: string?; processorFinishDetails: JsonDocument?; cubeColumns: JsonDocument?  
**Endpoint name:** `GetSolutions`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:24`

#### `POST /api/solution/buildCube/{solutionId}`

**Handler:** `BuildCube`  
**Назначение:** Построения куба для решения  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions_reports` → `view`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `solutionId: long`  
**Query:** —  
**Request body:** `—`  
**Request fields:** —  
**Response:** Не указан в metadata  
**Response fields:** —  
**Endpoint name:** `BuildCube`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:34`

#### `POST /api/solution/getCubeIntersectColumns`

**Handler:** `GetCubeIntersectColumns`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Cube Intersect Columns`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `IntersectColumnsRequest`  
**Request fields:** solutionIds: long[]  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "solutionIds": [
    0
  ]
}
```
**Endpoint name:** `GetCubeIntersectColumns`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:49`

#### `POST /api/solution/getSolutionIntersectColumns`

**Handler:** `GetSolutionIntersectColumns`  
**Назначение:** Назначение не документировано; по имени handler/route: `Get Solution Intersect Columns`.  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `view`  
**Безопасность:** Проверять семантику перед вызовом  
**Path:** —  
**Query:** —  
**Request body:** `IntersectColumnsRequest`  
**Request fields:** solutionIds: long[]  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "solutionIds": [
    0
  ]
}
```
**Endpoint name:** `GetSolutionIntersectColumns`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:47`

#### `POST /api/solution/setSolutionTitleOrDescription/{id}`

**Handler:** `SetTitleOrDescription`  
**Назначение:** Обновление наименования/описания решения  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** `id: long`  
**Query:** —  
**Request body:** `SetTitleDescriptionRequest`  
**Request fields:** title: string?; description: string?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "title": "<string>",
  "description": "<string>"
}
```
**Endpoint name:** `SetSolutionTitleOrDescription`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:29`

#### `POST /api/solution/solutions`

**Handler:** `PostSolution`  
**Назначение:** Создание решения  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Solution`  
**Request fields:** id: long; uniqueId: Guid?; projectId: long?; title: string?; description: string?; createUserId: long; createTs: DateTime; processorStartTs: DateTime?; processorFinishTs: DateTime?; processorStatus: ProcessorStatus; processorLog: string?; processorFinishDetails: JsonDocument?; cubeColumns: JsonDocument?  
**Response:** `201` → `Solution`  
**Response fields:** Solution => id: long; uniqueId: Guid?; projectId: long?; title: string?; description: string?; createUserId: long; createTs: DateTime; processorStartTs: DateTime?; processorFinishTs: DateTime?; processorStatus: ProcessorStatus; processorLog: string?; processorFinishDetails: JsonDocument?; cubeColumns: JsonDocument?  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "uniqueId": "<string>",
  "projectId": 0,
  "title": "<string>",
  "description": "<string>",
  "createUserId": 0,
  "createTs": "<string>",
  "processorStartTs": "<string>",
  "processorFinishTs": "<string>",
  "processorStatus": 0,
  "processorLog": "<string>",
  "processorFinishDetails": {},
  "cubeColumns": {}
}
```
**Endpoint name:** `AddSolution`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:26`

#### `PUT /api/solution/solutions`

**Handler:** `PutSolution`  
**Назначение:** Редактирование решения  
**Авторизация / ACS:** Access token required; ACS permission check + [Authorize]; ACS `solutions` → `change`  
**Безопасность:** ⚠️ Потенциально изменяет данные/состояние  
**Path:** —  
**Query:** —  
**Request body:** `Solution`  
**Request fields:** id: long; uniqueId: Guid?; projectId: long?; title: string?; description: string?; createUserId: long; createTs: DateTime; processorStartTs: DateTime?; processorFinishTs: DateTime?; processorStatus: ProcessorStatus; processorLog: string?; processorFinishDetails: JsonDocument?; cubeColumns: JsonDocument?  
**Response:** Не указан в metadata  
**Response fields:** —  

**JSON skeleton запроса:**

```json
{
  "id": 0,
  "uniqueId": "<string>",
  "projectId": 0,
  "title": "<string>",
  "description": "<string>",
  "createUserId": 0,
  "createTs": "<string>",
  "processorStartTs": "<string>",
  "processorFinishTs": "<string>",
  "processorStatus": 0,
  "processorLog": "<string>",
  "processorFinishDetails": {},
  "cubeColumns": {}
}
```
**Endpoint name:** `UpdateSolution`  
**Tags:** `Solution`  
**Источник:** `EST.WebApi.Controllers/SolutionController.cs:31`

## 7. DTO / модели

Восстановлено **128** публичных типов и **578** свойств.

### `AttributeSourceInfo`

**Полное имя:** `EST.WebApi.Models.DbModels.Imc.AttributeSourceInfo`  
**Базовые типы:** `—`  
**Схема:** source: string; hasTransformed: bool  

### `AuthRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Auth.AuthRequest`  
**Базовые типы:** `—`  
**Схема:** userAuthDto: UserAuthDto; terminalSessionRequest: TerminalSessionRequest  
**Локальные зависимости:** `UserAuthDto`  
**Внешние зависимости:** `TerminalSessionRequest`  

### `AuthResponse`

**Полное имя:** `EST.WebApi.Models.DbModels.AuthResponse`  
**Базовые типы:** `—`  
**Схема:** tokens: Tokens; terminalSessionResponse: TerminalSessionResponse; acsAuthorizationResponse: AcsBridgeCreateAuthorizationResponse  
**Локальные зависимости:** `Tokens`  
**Внешние зависимости:** `AcsBridgeCreateAuthorizationResponse, TerminalSessionResponse`  

### `BaseParameterDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.BaseParameterDto`  
**Базовые типы:** `—`  
**Схема:** iambParameters: IambParametersDto; elements: List<ElementDto>; groups: GroupsDto  
**Локальные зависимости:** `ElementDto, GroupsDto, IambParametersDto`  

### `BimIntersectionResultExtensions`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.BimIntersectionResultExtensions`  
**Базовые типы:** `—`  
**Схема:** —  

### `BoxDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.BoxDto`  
**Базовые типы:** `—`  
**Схема:** min: VertexDto; max: VertexDto  
**Локальные зависимости:** `VertexDto`  

### `CdbObjectTypeHierarchyDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Functions.CdbObjectTypeHierarchyDto`  
**Базовые типы:** `—`  
**Схема:** objectTypeId: long; parentObjectTypeId: long?; level: int; maxDepth: int; title: string  

### `ChainStatusDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Functions.ChainStatusDto`  
**Базовые типы:** `—`  
**Схема:** chainCode: string; isEnabled: bool  

### `CheckStatus`

**Полное имя:** `EST.WebApi.Models.Enums.CheckStatus`  
**Базовые типы:** `Enumeration`  
**Схема:** —  

### `CheckupCollisionsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.Collisions.CheckupCollisionsRequest`  
**Базовые типы:** `—`  
**Схема:** profileItemId: long; profileId: long; containerIds: long[]?  

### `ClearParamAlternateValueByElementsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.ClearParamAlternateValueByElementsRequest`  
**Базовые типы:** `—`  
**Схема:** containerId: long; elementIds: long[]  

### `ClearParamAlternateValueBySourcesRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.ClearParamAlternateValueBySourcesRequest`  
**Базовые типы:** `—`  
**Схема:** containerId: long; sourceIds: long[]?  

### `CollisionCheck`

**Полное имя:** `EST.WebApi.Models.DbModels.Checkup.Collisions.CollisionCheck`  
**Базовые типы:** `EntityBase, IEntityWithCreateTs, IEntityWithCreateUser`  
**Схема:** id: long; profileItemId: long; status: string; containerIds: long[]?; dependedProfileItemIds: long[]?; createTs: DateTime; createUserId: long  

### `CollisionContext`

**Полное имя:** `EST.WebApi.Models.DbModels.Checkup.Collisions.CollisionContext`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; contextId: Guid; containerIds: long[]; projectId: long  

### `CollisionParametersDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.CollisionParametersDto`  
**Базовые типы:** `—`  
**Схема:** iambParameters: IambParametersDto; elements: List<ElementDto>; groups: GroupsDto  
**Локальные зависимости:** `ElementDto, GroupsDto, IambParametersDto`  

### `CollisionReportRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.Collisions.CollisionReportRequest`  
**Базовые типы:** `—`  
**Схема:** profileId: long; containerIds: long[]; reportTypeIsBI: bool; collisionTypeReportDatas: CollisionTypeReportData[]  
**Локальные зависимости:** `CollisionTypeReportData`  

### `CollisionResult`

**Полное имя:** `EST.WebApi.Models.DbModels.Checkup.Collisions.CollisionResult`  
**Базовые типы:** `EntityBase, IEntityWithCreateTs, IEntityWithUpdateTs, IEntityWithUpdateUser`  
**Схема:** id: long; collisionCheckId: long; elementId1: long; elementId2: long?; element1: ImcElement; element2: ImcElement?; meshes: byte[]?; meshVolumes: JsonDocument?; aaBoundingBoxes: JsonDocument?; aaVolumes: JsonDocument?; oBoundingBoxes: JsonDocument?; obbVolumes: JsonDocument?; status: CollisionStatus; priority: CollisionPriority; comment: string?; createTs: DateTime; updateTs: DateTime?; updateUserId: long?; distance: double?; counter: int  
**Локальные зависимости:** `ImcElement`  
**Внешние зависимости:** `CollisionPriority, CollisionStatus`  

### `CollisionResultDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.CollisionResultDto`  
**Базовые типы:** `—`  
**Схема:** elementId1: long; elementId2: long; meshes: List<MeshDto>; meshVolumes: List<double>; aaBoundingBoxes: List<BoxDto>; aaVolumes: List<double>; oBoundingBoxes: List<BoxDto>; obbVolumes: List<double>  
**Локальные зависимости:** `BoxDto, MeshDto`  

### `CollisionStatistics`

**Полное имя:** `EST.WebApi.Models.DbModels.Checkup.Collisions.CollisionStatistics`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; collisionCheckId: long; detectedCount: int; activeCount: int; fixedCount: int; createTs: DateTime  

### `CollisionTypeReportData`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.Collisions.CollisionTypeReportData`  
**Базовые типы:** `—`  
**Схема:** validationTypeName: string; shortValidationTypeName: string; profileItemIds: long[]; image: bool; status: bool; comment: bool; priority: bool; collisionVolume: bool; boundingBoxVolume: bool; boundingBoxSize: bool; distance: bool; errorType: bool; count: bool; priorities: CollisionPriority[]; additionalParameters: ParameterDefinitionHook[]  
**Внешние зависимости:** `CollisionPriority, ParameterDefinitionHook`  

### `ComparisonReportRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.ComparisonReportRequest`  
**Базовые типы:** `ReportRequest`  
**Схема:** isReportMode: bool; customData: CustomDataGridJsonModel; solutionIds: long[]  
**Внешние зависимости:** `CustomDataGridJsonModel`  

### `Component`

**Полное имя:** `EST.WebApi.Models.DbModels.Component`  
**Базовые типы:** `EntityBase, IEntityWithCreateTs, IEntityWithCreateUser, IEntityWithUpdateTs, IEntityWithUpdateUser, IEntityWithUniqueId`  
**Схема:** id: long; uniqueId: Guid?; parentId: long?; projectId: long?; solutionId: long?; componentType: ProjectComponentType; content: JsonDocument?; title: string?; isEnabled: bool?; description: string?; tags: JsonDocument?; createTs: DateTime; createUserId: long; updateTs: DateTime?; updateUserId: long?; attributes: JsonDocument?  
**Локальные зависимости:** `ProjectComponentType`  

### `ConditionData`

**Полное имя:** `EST.WebApi.Models.DbModels.ConditionData`  
**Базовые типы:** `EntityBase, ICloneable<ConditionData>`  
**Схема:** id: long; body: JsonDocument?; hasElements: bool; isActual: bool; hash: string; projectId: int  

### `CreateImcParameterDefinitionRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.CreateImcParameterDefinitionRequest`  
**Базовые типы:** `—`  
**Схема:** elementMaps: ElementMap[]; code: string; isNumeric: bool; uom: string?; numericValue: decimal?; stringValue: string?  
**Локальные зависимости:** `ElementMap`  

### `DeleteElementsGeometryRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.DeleteElementsGeometryRequest`  
**Базовые типы:** `—`  
**Схема:** elementsWithContainerIds: ElementsWithContainerId[]  
**Локальные зависимости:** `ElementsWithContainerId`  

### `DeleteImcElementsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.DeleteImcElementsRequest`  
**Базовые типы:** `—`  
**Схема:** elementsWithContainerIds: ElementsWithContainerId[]  
**Локальные зависимости:** `ElementsWithContainerId`  

### `DistanceParametersDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.DistanceParametersDto`  
**Базовые типы:** `BaseParameterDto`  
**Схема:** iambParameters: IambParametersDto; elements: List<ElementDto>; groups: GroupsDto; minimalDistance: double  
**Локальные зависимости:** `ElementDto, GroupsDto, IambParametersDto`  

### `DistanceResultDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.DistanceResultDto`  
**Базовые типы:** `—`  
**Схема:** elementId1: long; elementId2: long; distance: double  

### `DuplicationParametersDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.DuplicationParametersDto`  
**Базовые типы:** `—`  
**Схема:** iambParameters: IambParametersDto; elements: List<ElementDto>; groups: GroupsDto  
**Локальные зависимости:** `ElementDto, GroupsDto, IambParametersDto`  

### `DuplicationResultDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.DuplicationResultDto`  
**Базовые типы:** `—`  
**Схема:** elementId1: long; elementId2: long  

### `ElementActionMapDto`

**Полное имя:** `EST.WebApi.Models.Dtos.ElementActionMapDto`  
**Базовые типы:** `—`  
**Схема:** elementId: long; actionCount: int; workCount: int  

### `ElementDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.ElementDto`  
**Базовые типы:** `—`  
**Схема:** id: long; meshes: List<MeshDto>  
**Локальные зависимости:** `MeshDto`  

### `ElementDtoComparer`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.ElementDtoComparer`  
**Базовые типы:** `IEqualityComparer<ElementDto>`  
**Схема:** —  

### `ElementHanlersTreeRowDto`

**Полное имя:** `EST.WebApi.Models.Dtos.ElementHanlersTreeRowDto`  
**Базовые типы:** `—`  
**Схема:** nodeId: long; parentNodeId: long; cdbItemCode: string; cdbItemTitle: string; quantity: double; metrics: string  

### `ElementMap`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.ElementMap`  
**Базовые типы:** `—`  
**Схема:** containerId: long; elementIds: long[]  

### `ElementsByProfileDto`

**Полное имя:** `EST.WebApi.Models.ElementsByProfileDto`  
**Базовые типы:** `—`  
**Схема:** elements: ImcElement[]?; paramDefs: ImcParameterDefinition[]?; paramValues: ImcParameterValue[]?  
**Локальные зависимости:** `ImcElement, ImcParameterDefinition, ImcParameterValue`  

### `ElementsWithContainerId`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.ElementsWithContainerId`  
**Базовые типы:** `—`  
**Схема:** containerId: long; elementIds: long[]  

### `EntityBase`

**Полное имя:** `EST.WebApi.Models.DbModels.EntityBase`  
**Базовые типы:** `IEntityBase`  
**Схема:** id: long  

### `Enumeration`

**Полное имя:** `EST.WebApi.Models.Enums.Enumeration`  
**Базовые типы:** `IComparable`  
**Схема:** —  

### `ErrorDetails`

**Полное имя:** `EST.WebApi.Models.Dtos.ErrorDetails`  
**Базовые типы:** `—`  
**Схема:** statusCode: HttpStatusCode; message: string?  
**Внешние зависимости:** `HttpStatusCode`  

### `ErrorLog`

**Полное имя:** `EST.WebApi.Models.Dtos.Auth.ErrorLog`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; createTs: DateTime; showTs: DateTime?; sqlCmd: string?; errorMessageText: string?; errorMessageDetail: string?; errorMessageHint: string?  

### `FaceDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.FaceDto`  
**Базовые типы:** `—`  
**Схема:** a: int; b: int; c: int  

### `FlywaySchemaHistory`

**Полное имя:** `EST.WebApi.Models.DbModels.FlywaySchemaHistory`  
**Базовые типы:** `—`  
**Схема:** installedRanc: int; version: string; description: string; type: string; script: string; checkSum: int; installedBy: string; installedOn: DateTime; executionTime: int; success: bool  

### `FunctionName`

**Полное имя:** `EST.WebApi.Models.DbModels.FunctionName`  
**Базовые типы:** `—`  
**Схема:** —  

### `GetElementByProfileItemRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.GetElementByProfileItemRequest`  
**Базовые типы:** `—`  
**Схема:** projectId: long; getElements: bool; getGrefs: bool; containerIds: long[]; profileItemId: long?; getElements1: bool; getElements2: bool; includeParentConditions: bool; includeChildConditions: bool; includeToElementsGroupingFields: bool; loadDetails: bool  

### `GetElementByProfileItemResponse`

**Полное имя:** `EST.WebApi.Models.Dtos.Responses.Imc.GetElementByProfileItemResponse`  
**Базовые типы:** `—`  
**Схема:** elements1: ExpandoObject[]; elements2: ExpandoObject[]; imcGrefs1: ImcGrefDto[]; imcGrefs2: ImcGrefDto[]; elementIds1: long[]; elementIds2: long[]  
**Локальные зависимости:** `ImcGrefDto`  

### `GetElementsByConditionsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.GetElementsByConditionsRequest`  
**Базовые типы:** `—`  
**Схема:** containerIds: long[]?; sourceIds: long[]?; filter: string?; conditionBlock: ConditionsBlock?; availableElementIds: long[]?; availableElementGuids: string[]?; hooks: ParameterDefinitionHook[]  
**Внешние зависимости:** `ConditionsBlock, ParameterDefinitionHook`  

### `GetElementsBySelectorsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.GetElementsBySelectorsRequest`  
**Базовые типы:** `—`  
**Схема:** containerIds: long[]?; filter: string?; columnParamDefinitionIds: long[]?; availableElementIds: long[]?; elementUniqueIds: string[]?; sourceIds: long?[]?  

### `GetElementsByStructureRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.GetElementsByStructureRequest`  
**Базовые типы:** `GetElementByProfileItemRequest`  
**Схема:** projectId: long; getElements: bool; getGrefs: bool; containerIds: long[]; profileItemId: long?; getElements1: bool; getElements2: bool; includeParentConditions: bool; includeChildConditions: bool; includeToElementsGroupingFields: bool; loadDetails: bool; filterSequence: List<StructureFilter>  
**Локальные зависимости:** `StructureFilter`  

### `GetGroupedCollisionElementsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.Collisions.GetGroupedCollisionElementsRequest`  
**Базовые типы:** `—`  
**Схема:** profileItemId: long; containerIds: long[]; parameter: SimpleParameterDefinitionHook  
**Внешние зависимости:** `SimpleParameterDefinitionHook`  

### `GetGroupedCollisionElementsResponce`

**Полное имя:** `EST.WebApi.Models.Dtos.Responses.GetGroupedCollisionElementsResponce`  
**Базовые типы:** `—`  
**Схема:** —  

### `GetImcElementGeometryRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.GetImcElementGeometryRequest`  
**Базовые типы:** `LargeDataRequest`  
**Схема:** take: int; skip: int; elementIds: long[]?  

### `GetImcHasGeometryRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.GetImcHasGeometryRequest`  
**Базовые типы:** `—`  
**Схема:** containerIds: long[]?  

### `GetImcSourceGeometryRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.GetImcSourceGeometryRequest`  
**Базовые типы:** `LargeDataRequest`  
**Схема:** take: int; skip: int; sourceIds: long[]?  

### `GetStatusesRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.GetStatusesRequest`  
**Базовые типы:** `—`  
**Схема:** profileItemId: long; percents: int[]?  

### `GlobalComponent`

**Полное имя:** `EST.WebApi.Models.DbModels.GlobalComponent`  
**Базовые типы:** `EntityBase, IEntityWithUpdateTs`  
**Схема:** id: long; componentType: GlobalComponentType?; content: JsonDocument?; updateTs: DateTime?; updateUserId: long?  
**Локальные зависимости:** `GlobalComponentType`  

### `GroupsDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.GroupsDto`  
**Базовые типы:** `—`  
**Схема:** a: List<long>; b: List<long>  

### `IambParametersDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.IambParametersDto`  
**Базовые типы:** `—`  
**Схема:** fracAlpha: double; fracOffset: double; oobPrescisionStep: long  

### `ImcAdapterQueue`

**Полное имя:** `EST.WebApi.Models.DbModels.Imc.ImcAdapterQueue`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; index: int?; adapterId: long?; containerId: long?; title: string?  

### `ImcAdapterTrace`

**Полное имя:** `EST.WebApi.Models.DbModels.Imc.ImcAdapterTrace`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; containerId: long; parameterValueId: long; parameterDefinitionId: long; sourceType: short; hasTransformed: bool  

### `ImcContainer`

**Полное имя:** `EST.WebApi.Models.DbModels.Imc.ImcContainer`  
**Базовые типы:** `EntityBase, IEntityWithUpdateTs, IEntityWithUpdateUser, IEntityWithUniqueId, IEntityWithReceiveId`  
**Схема:** id: long; projectId: long?; solutionId: long?; uniqueId: Guid?; title: string?; attributes: JsonDocument?; offset: JsonDocument?; isEnabled: bool?; description: string?; updateTs: DateTime?; updateUserId: long?; receiveId: long?; extractorStartTs: DateTime?; extractorFinishTs: DateTime?; extractorStatus: ImcExtractStatus?; extractorLog: string?; sourceType: BimSourceType?; adapterStatus: ImcAdaptationStatus?; version: int; isVisible: bool; updateGeometryTs: DateTime?; adapterLog: string?; adapterHash: string?  
**Локальные зависимости:** `BimSourceType, ImcAdaptationStatus, ImcExtractStatus`  

### `ImcElement`

**Полное имя:** `EST.WebApi.Models.DbModels.Imc.ImcElement`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; containerId: long; sourceId: long?; title: string?; uniqueId: string?; nativeId: string?; transformation: byte[]?; grefId: long?; onReceiveId: long?  

### `ImcExportRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.ImcExportRequest`  
**Базовые типы:** `—`  
**Схема:** projectId: long; containerIds: long[]  

### `ImcGref`

**Полное имя:** `EST.WebApi.Models.DbModels.Imc.ImcGref`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; containerId: long?; geometry: byte[]?; elementId: long  

### `ImcGrefDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Imc.ImcGrefDto`  
**Базовые типы:** `—`  
**Схема:** id: long; containerId: long?; geometry: byte[]?; elementIds: long[]; elementTransformations: byte[][]  

### `ImcParameterDefinition`

**Полное имя:** `EST.WebApi.Models.DbModels.Imc.ImcParameterDefinition`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; containerId: long; title: string?; isNumeric: bool; layer: short?; description: string?; code: string?; dataTypeNativeName: string?; uom: string?; unitType: string?; reportColumnType: short?  

### `ImcParameterValue`

**Полное имя:** `EST.WebApi.Models.DbModels.Imc.ImcParameterValue`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; elementId: long; containerId: long; parameterDefinitionId: long; originValueNumeric: decimal?; alternativeValueNumeric: decimal?; originValueString: string?; alternativeValueString: string?; onAlternative: bool?; code: string?; isNumeric: bool; layer: short?; sourceInfo: AttributeSourceInfo  
**Локальные зависимости:** `AttributeSourceInfo`  

### `ImcSource`

**Полное имя:** `EST.WebApi.Models.DbModels.Imc.ImcSource`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; value: string?; containerId: long  

### `ImcSourceDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Imc.ImcSourceDto`  
**Базовые типы:** `—`  
**Схема:** id: long; value: string?; containerId: long; elementCount: int; geometryCount: int  

### `ImcUploadRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.ImcUploadRequest`  
**Базовые типы:** `UploadRequest`  
**Схема:** title: string?; projectId: long; oldContainerId: long?  

### `IntersectColumnsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.IntersectColumnsRequest`  
**Базовые типы:** `—`  
**Схема:** solutionIds: long[]  

### `IsEnableProfileItemRequest`

**Полное имя:** `EST.API.Client.Models.Requests.IsEnableProfileItemRequest`  
**Базовые типы:** `—`  
**Схема:** profileItemId: long; isEnabled: bool  

### `LargeDataRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.LargeDataRequest`  
**Базовые типы:** `—`  
**Схема:** take: int; skip: int  

### `Larix_Localization_Resources_`

**Полное имя:** `EST.WebApi.Models.SharedResources.Larix_Localization_Resources_`  
**Базовые типы:** `—`  
**Схема:** —  

### `MeshDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.MeshDto`  
**Базовые типы:** `—`  
**Схема:** vertices: List<VertexDto>; faces: List<FaceDto>  
**Локальные зависимости:** `FaceDto, VertexDto`  

### `MeshDtoExtensions`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.MeshDtoExtensions`  
**Базовые типы:** `—`  
**Схема:** —  

### `MinimalVerticalDistanceParametersDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.MinimalVerticalDistanceParametersDto`  
**Базовые типы:** `—`  
**Схема:** iambParameters: IambParametersDto; elements: List<ElementDto>; groups: GroupsDto  
**Локальные зависимости:** `ElementDto, GroupsDto, IambParametersDto`  

### `ParameterCheck`

**Полное имя:** `EST.WebApi.Models.DbModels.Checkup.Parameters.ParameterCheck`  
**Базовые типы:** `EntityBase, IEntityWithCreateTs, IEntityWithCreateUser`  
**Схема:** id: long; profileItemId: long; status: string; containerIds: long[]?; dependedProfileItemIds: long[]?; createTs: DateTime; createUserId: long  

### `ParameterCheckCondition`

**Полное имя:** `EST.WebApi.Models.DbModels.Checkup.Parameters.ParameterCheckCondition`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; profileItemId: long; validationParameterId: long?; parentId: long?; isGroup: bool; isEnabled: bool; logicalOperator: LogicalOperator?; isNot: bool?; comparisonOperator: ComparisonOperator?; value: string?; useRegistry: bool; spaceIgnore: bool  
**Внешние зависимости:** `ComparisonOperator, LogicalOperator`  

### `ParameterResult`

**Полное имя:** `EST.WebApi.Models.DbModels.Checkup.Parameters.ParameterResult`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; parameterCheckId: long; elementId: long; details: JsonDocument?  

### `ParameterValidationTypeReportData`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.Parameters.ParameterValidationTypeReportData`  
**Базовые типы:** `—`  
**Схема:** reportName: string; isCheckedValidateItemName: bool; additionalParameters: ParameterDefinitionHook[]  
**Внешние зависимости:** `ParameterDefinitionHook`  

### `ParameterValueChanger`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.ParameterValueChanger`  
**Базовые типы:** `—`  
**Схема:** elementNativeUniqueId: string; parameterCode: string; parameterIsDirectly: bool; originalValueString: string; alternativeValueString: string  

### `ParameterValuesChangeList`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.ParameterValuesChangeList`  
**Базовые типы:** `—`  
**Схема:** application: string; container: string; author: string; timeCreate: DateTime; parameterValueChangers: List<ParameterValueChanger>  
**Локальные зависимости:** `ParameterValueChanger`  

### `ParameterValuesRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.ParameterValuesRequest`  
**Базовые типы:** `—`  
**Схема:** projectId: long; containerIds: long[]; applicationName: string; container: string  

### `ProcessCalculationRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.ProcessCalculationRequest`  
**Базовые типы:** `—`  
**Схема:** projectId: long; title: string; description: string  

### `Profile`

**Полное имя:** `EST.WebApi.Models.DbModels.Profile.Profile`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; projectId: long?; title: string?; comment: string?; profileType: ProfileType  
**Локальные зависимости:** `ProfileType`  

### `ProfileCheckupRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.ProfileCheckupRequest`  
**Базовые типы:** `—`  
**Схема:** projectId: long; profileId: long; containerIds: long[]  

### `ProfileElementMap`

**Полное имя:** `EST.WebApi.Models.DbModels.Profile.ProfileElementMap`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; containerId: long?; profileItemId: long?; elementUniqueId: string?; date: DateTime; percent: int; profileId: int  

### `ProfileItem`

**Полное имя:** `EST.WebApi.Models.DbModels.Profile.ProfileItem`  
**Базовые типы:** `EntityBase, ICloneable<ProfileItem>, ICloneable, IIndexable`  
**Схема:** id: long; profileId: long?; parentId: long?; title: string?; comment: string?; type: short; containerId: long?; isEnabled: bool; groupFieldParamCodes: JsonDocument?; extFieldParamCodes: JsonDocument?; condition1: ConditionData?; condition2: ConditionData?; condition1Id: long?; condition2Id: long?; parentCondition1Id: long?; parentCondition2Id: long?; elementGuids1: string[]?; elementGuids2: string[]?; parentElementGuids1Id: long?; parentElementGuids2Id: long?; color: JsonDocument?; camera: JsonDocument?; itemParams: JsonDocument?; isFolder: bool; index: int  
**Локальные зависимости:** `ConditionData`  

### `ProfileItemIndexUpdateMap`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.ProfileItemIndexUpdateMap`  
**Базовые типы:** `IEntityBase, IIndexable`  
**Схема:** id: long; index: int  

### `ProfileItemIndexUpdateRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.ProfileItemIndexUpdateRequest`  
**Базовые типы:** `—`  
**Схема:** profileId: long; map: ProfileItemIndexUpdateMap[]  
**Локальные зависимости:** `ProfileItemIndexUpdateMap`  

### `Project`

**Полное имя:** `EST.WebApi.Models.DbModels.Project`  
**Базовые типы:** `EntityBase, IEntityWithCreateTs, IEntityWithCreateUser, IEntityWithUniqueId, IEntityWithReceiveId`  
**Схема:** id: long; uniqueId: Guid?; title: string?; description: string?; createTs: DateTime; createUserId: long; user: User?; receiveId: long?; cdbSourceUniqueId: string?; cdbSourceTarget: CDBSourceTarget?; author: UserDto?  
**Локальные зависимости:** `CDBSourceTarget, User, UserDto`  

### `Receive`

**Полное имя:** `EST.WebApi.Models.DbModels.Receive`  
**Базовые типы:** `EntityBase, IEntityWithCreateTs, IEntityWithCreateUser`  
**Схема:** id: long; parentId: long?; createTs: DateTime; createUserId: long; finishUploadTs: DateTime?; finishExtractTs: DateTime?; hash: string?; status: TaskStatus; sourceType: BimSourceType; sourceOriginName: string?; sourceSize: long?; isStored: bool; logUpload: string?; logExtract: string?  
**Локальные зависимости:** `BimSourceType`  
**Внешние зависимости:** `TaskStatus`  

### `ReceiveRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.ReceiveRequest`  
**Базовые типы:** `—`  
**Схема:** filePath: string; fileName: string; sourceType: BimSourceType; uploadRequest: JsonDocument?  
**Локальные зависимости:** `BimSourceType`  

### `ReportRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.ReportRequest`  
**Базовые типы:** `—`  
**Схема:** isReportMode: bool; customData: CustomDataGridJsonModel  
**Внешние зависимости:** `CustomDataGridJsonModel`  

### `RequestBase`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.RequestBase`  
**Базовые типы:** `—`  
**Схема:** id: long?; projectId: long?  

### `SetImcParameterDefinitionRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.SetImcParameterDefinitionRequest`  
**Базовые типы:** `—`  
**Схема:** containerIds: long[]; parameterCodes: string[]; parameterLayer: ParameterLayer?  
**Внешние зависимости:** `ParameterLayer`  

### `SetIsEnabledRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.SetIsEnabledRequest`  
**Базовые типы:** `—`  
**Схема:** isEnabled: bool  

### `SetParamAlternateValueByElementsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.SetParamAlternateValueByElementsRequest`  
**Базовые типы:** `—`  
**Схема:** containerIds: ElementsWithContainerId[]; parameterCode: string; isNumeric: bool; numericValue: decimal?; stringValue: string?  
**Локальные зависимости:** `ElementsWithContainerId`  

### `SetParamAlternateValueBySourcesRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.SetParamAlternateValueBySourcesRequest`  
**Базовые типы:** `—`  
**Схема:** containerId: long; parameterCode: string; sourceIds: long[]?; isNumeric: bool; numericValue: decimal?; stringValue: string?  

### `SetStageDataRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Functions.SetStageDataRequest`  
**Базовые типы:** `—`  
**Схема:** componentId: long; guids: string[]?  

### `SetStageIsEnabledRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Functions.SetStageIsEnabledRequest`  
**Базовые типы:** `SetStageDataRequest`  
**Схема:** componentId: long; guids: string[]?; isEnabled: bool  

### `SetTagsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.SetTagsRequest`  
**Базовые типы:** `—`  
**Схема:** tags: JsonDocument?  

### `SetTitleDescriptionRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.SetTitleDescriptionRequest`  
**Базовые типы:** `SetTitleRequest`  
**Схема:** title: string?; description: string?  

### `SetTitleRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.SetTitleRequest`  
**Базовые типы:** `—`  
**Схема:** title: string?  

### `Solution`

**Полное имя:** `EST.WebApi.Models.DbModels.Solution`  
**Базовые типы:** `EntityBase, IEntityWithCreateTs, IEntityWithCreateUser, IEntityWithUniqueId`  
**Схема:** id: long; uniqueId: Guid?; projectId: long?; title: string?; description: string?; createUserId: long; createTs: DateTime; processorStartTs: DateTime?; processorFinishTs: DateTime?; processorStatus: ProcessorStatus; processorLog: string?; processorFinishDetails: JsonDocument?; cubeColumns: JsonDocument?  
**Локальные зависимости:** `ProcessorStatus`  

### `SolutionAceqTransaction`

**Полное имя:** `EST.WebApi.Models.DbModels.SolutionAceqTransaction`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; solutionId: int; handlerActionId: int; cdbNodeId: int; elementId: long; activityCode: string; quantity: double; expenditure: double; indicatorValues: double[]?; transition: JsonDocument  

### `StructureFilter`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.StructureFilter`  
**Базовые типы:** `—`  
**Схема:** parameterCode: string; parameterValue: string  

### `TaskQueue`

**Полное имя:** `EST.WebApi.Models.DbModels.TaskQueue`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; parentId: long?; rootParentId: long?; taskType: string; requestBody: string?; externalResponse: string?; status: string?; percent: int; startTs: DateTime?; finishTs: DateTime?; queueTs: DateTime; userId: long?; errorDetails: string?  

### `TaskQueueStatus`

**Полное имя:** `EST.WebApi.Models.Enums.TaskQueueStatus`  
**Базовые типы:** `Enumeration`  
**Схема:** —  

### `TaskQueueType`

**Полное имя:** `EST.WebApi.Models.Enums.TaskQueueType`  
**Базовые типы:** `Enumeration`  
**Схема:** —  

### `TokenDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Auth.TokenDto`  
**Базовые типы:** `—`  
**Схема:** accessToken: string?; refreshToken: string?  

### `TokenTime`

**Полное имя:** `EST.WebApi.Core.TokenTime`  
**Базовые типы:** `—`  
**Схема:** —  

### `Tokens`

**Полное имя:** `EST.WebApi.Models.DbModels.Tokens`  
**Базовые типы:** `—`  
**Схема:** accessToken: string?; refreshToken: string?  

### `TreeItemDto`

**Полное имя:** `EST.WebApi.Models.Dtos.TreeItemDto`  
**Базовые типы:** `—`  
**Схема:** title: string; children: List<TreeItemDto>  

### `UpdateCollisionResultCommentsRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.Collisions.UpdateCollisionResultCommentsRequest`  
**Базовые типы:** `—`  
**Схема:** collisionResultIds: long[]; comment: string  

### `UpdateCollisionResultPrioritiesRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.Collisions.UpdateCollisionResultPrioritiesRequest`  
**Базовые типы:** `—`  
**Схема:** collisionResultIds: long[]; priority: CollisionPriority  
**Внешние зависимости:** `CollisionPriority`  

### `UpdateCollisionResultRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.Collisions.UpdateCollisionResultRequest`  
**Базовые типы:** `—`  
**Схема:** collisionResultId: long; priority: CollisionPriority; comment: string?  
**Внешние зависимости:** `CollisionPriority`  

### `UpdateImcSourceRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Imc.UpdateImcSourceRequest`  
**Базовые типы:** `—`  
**Схема:** sourceIds: long[]; newValue: string  

### `UploadRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.UploadRequest`  
**Базовые типы:** `—`  
**Схема:** —  

### `User`

**Полное имя:** `EST.WebApi.Models.DbModels.User`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; acsLogin: string?; acsId: long?; isDeleted: bool  

### `UserAuthDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Auth.UserAuthDto`  
**Базовые типы:** `—`  
**Схема:** login: string?; password: string?  

### `UserDto`

**Полное имя:** `EST.WebApi.Models.Dtos.UserDto`  
**Базовые типы:** `—`  
**Схема:** id: long; acsLogin: string?  

### `UserRefreshTokens`

**Полное имя:** `EST.WebApi.Models.Dtos.Auth.UserRefreshTokens`  
**Базовые типы:** `—`  
**Схема:** userName: string?; refreshToken: string?  

### `ValidationParameter`

**Полное имя:** `EST.WebApi.Models.DbModels.Checkup.Parameters.ValidationParameter`  
**Базовые типы:** `EntityBase`  
**Схема:** id: long; profileId: long?; code: string; isNumeric: bool; acceptableValueRules: string?; comment: string?  

### `ValidationParameterErrorDto`

**Полное имя:** `EST.WebApi.DataAccess.Repositories.Imc.ValidationParameterErrorDto`  
**Базовые типы:** `—`  
**Схема:** elementId: long; elementNativeId: string; parameterId: long?; parameterCode: string?; parameterIsNumeric: bool?; parameterValueId: long?; parameterStringValue: string?; parameterNumericValue: decimal?  

### `ValidationReportRequest`

**Полное имя:** `EST.WebApi.Models.Dtos.Requests.Checkup.Parameters.ValidationReportRequest`  
**Базовые типы:** `—`  
**Схема:** profileId: long; containerIds: long[]; reportTypeIsBI: bool; addAttributeSourceInfo: bool; datas: ParameterValidationTypeReportData[]  
**Локальные зависимости:** `ParameterValidationTypeReportData`  

### `VertexDto`

**Полное имя:** `EST.WebApi.Models.Dtos.Checkup.Collisions.VertexDto`  
**Базовые типы:** `—`  
**Схема:** x: double; y: double; z: double  

## 8. Enum

- **AdditionalFiltering**: `None=0`, `IncludeParentConditions=1`, `IncludeChildConditions=2`, `IncludeParentAndChildConditions=4`, `ExcludeParentConditions=8`
- **BimSourceType**: `Imc=0`, `Ifc=1`, `Excel=2`
- **CDBSourceTarget**: `GlobalComponent=0`, `ProjectComponent=1`
- **GlobalComponentType**: `AttributeTree=1`, `Extension=2`, `SourceList=3`
- **ImcAdaptationStatus**: `NotStarted=0`, `AdaptationInitialization=10`, `ClearData=20`, `FillMirrorExportAndCustom=30`, `ReadAdapters=40`, `ReadAttributeTree=41`, `ReadParameterDefinitions=42`, `ReadElementsWithValues=43`, `ReadAggregateValues=44`, `AdaptationInProcess=50`, `InsertParameterDefinitions=60`, `InsertParameterValues=61`, `TracingReceiptValues=62`, `TraceValuesWriting=63`, `FillMirrorAdapter=70`, `DeleteNotUsedParameterDefinitions=80`, `UpdateContainerAdapterHash=81`, `FinishedWellDone=100`, `FinishedWithError=110`, `FinishedByStop=120`, `Removed=130`
- **ImcExtractStatus**: `NotStarted=0`, `ExtractInitialization=10`, `SourceContainerReading=20`, `TargetContainerCreating=30`, `InsertSources=40`, `InsertGeometries=41`, `InsertElements=42`, `InsertParameterDefinitions=43`, `InsertParameterValues=44`, `ReIndexation=50`, `ClearingTempData=60`, `RollBackData=70`, `FinishedWellDone=100`, `FinishedWithError=110`, `FinishedByStop=120`, `Update=200`
- **ProcessorStatus**: `NotStarted=0`, `CreatingSolutionInfrastructure=10`, `AdaptationProjectModels=20`, `AggregationSolutionModel=21`, `ReadingCdb=30`, `ReadingGlobalEnvironment=31`, `ReadingLocalEnvironment=32`, `ReadingProjectStagesAndChains=33`, `CheckCdbIndexes=34`, `CheckCdbNodeCodes=35`, `ReadingElementsParameterValues=36`, `CalculatingBuildFarmQTF=40`, `CalculatingBuildChainIndex=41`, `CalculatingACEQ=42`, `CalculatingRemoveEmptyTailsACEQ=43`, `CalculatingACEQVerticalRecalc=44`, `CalculatingACEQHorizontalRecalc=45`, `CalculatingWriteACEQ=46`, `CalculatingWriteSolutionColumns=47`, `CalculatingWriteCdbDenormalizedTree=48`, `FinishedWellDone=100`, `FinishedWithError=110`, `FinishedByStop=120`
- **ProfileType**: `Model=0`, `Struct=1`, `Set=2`, `Status=3`, `View=4`, `ParameterValidation=5`, `ClashDetection=6`, `ElementList=7`, `ClashReport=8`, `ClashBIReport=9`, `ParameterValidationReport=10`, `ParameterValidationBIReport=11`
- **ProjectComponentType**: `Pivot=5`, `ColumnSet=6`, `Aceq=14`, `CollisionProfileResult=19`, `Log=17`, `CompilationErrors=15`, `AttributeTree=1`, `Adapter=2`, `Chart=3`, `ChainProcess=4`, `ChainSeparator=20`, `Constants=7`, `StatusList=8`, `StatusModels=9`, `ElementsSnapshots=10`, `ValidateParameters=11`, `ModelParameterValidationProfile=12`, `CollisionValidateProfile=13`, `SolutionJournal=16`, `SolutionLog=18`, `SolutionColumns=21`, `SolutionColumnsSet=22`, `SolutionScope=24`, `SolutionQTFCodeSource=25`, `CdbContainer=23`, `Report=26`, `CdbObjectTypeMapping=27`, `GGETypeMapping=28`

## 9. Пока не восстановленные внешние типы

- `ActivationStatus`
- `LicensePeriod`
- `ParameterLayer`
- `RecipientLicenseActivatorResponse`
- `TerminalSessionResponse`

## 10. Что дать другому чату

Достаточно приложить **этот файл** и написать задачу, например:

> Используй приложенный `Larix_API_Context_for_AI.md` как единственный источник по внутреннему API Larix. Напиши Python-клиент, который авторизуется, получает список проектов и проверяет наличие моделей и структуры. Не придумывай поля/endpoint'ы, которых нет в справочнике. Изменяющие запросы не выполняй без моего явного указания.

## 11. Ограничения

- API reverse-engineered и не является официальным публичным контрактом Larix.
- После обновления Larix необходимо повторно проверять `/getApiVersion` и при необходимости пересобирать каталог.
- Некоторые endpoint'ы имеют XML-summary, некоторые описаны только по route/handler; такие места прямо помечены как недокументированные.
- Наличие endpoint'а не гарантирует, что текущий пользователь имеет ACS-разрешение на его вызов.