##1.	프로젝트 주제 (Project topic)

부산대학교 근처의 종교활동 권유 및 설문조사 관련 정보를 공유하기 위한 웹사이트를 만든다. 사용자는 회원가입을 진행하고, 해당 설문조사나 종교활동 권유를 당한 위치, 인원, 말하는 줄거리, 시각을 사이트에 공유하고, 지도에 나타내고 이를 데이터베이스에 저장 또는 갱신한다. 사이트에서 이 정보를 공유한다. 해당 정보에 대한 수정, 댓글 기능 및 공감기능도 만든다.

##2.	사용자 (역할) (Users / Roles)

해당 웹사이트를 이용하는 사용자로는 guest, user, admin이 있다.
Guest는 회원가입을 진행하지 않은 사용자로 정보열람에 제한이 있다.
User는 회원가입을 한 사용자로 정보 공유 및 게시글, 댓글 작성 및 신고 할 수 있다. 정보열람에도 제한이 없다.
Admin은 관리자로 부적절한 정보 및 댓글 삭제와 회원 관리를 할 수 있다. 


##3.	기능 (Functions)

guest
-	회원가입 : 사이트에 회원가입을 한다. 
아이디, 비밀번호, 이름, 이메일을 입력하고 회원가입을 한다. 이는 User 테이블에 where절로 중복을 검사하고 INSERT하는 과정으로 진행한다.
회원가입 이후엔 user 데이터베이스에 등록되어 정보를 모두 열람할 수 있다. 회원가입 과정은 transaction으로 진행한다.
-	정보 조회 : 일부 제한된 정보를 열람할 수 있다. 
-	추천/비추천 : 다른 정보에 추천 및 비추천을 할 수 있다. UPDATE로 Information 테이블의 recommended, not_recommended를 수정한다.
User
-	회원탈퇴 : 사이트에서 탈퇴한다. DELETE로 User 테이블에서 삭제한다. user_id를 참조하는 레코드들은 cascade로 삭제한다.
-	정보 조회 : 제한없이 모든 information 데이터베이스의 정보를 열람할 수 있다. 
-	정보 등록 : information 데이터베이스에 자신의 정보를 공유할 수 있다. INSERT로 Information 데이터베이스에 정보를 공유한다.
-	정보 삭제 : 자신이 쓴 글을 삭제할 수 있다. Info_id를 참조하는 comment 데이터베이스의 레코드는 cascade로 삭제한다.
-	댓글 작성 및 삭제 : 정보에 대한 댓글을 작성할 수 있다. Comment 테이블에 INSERT 및 DELETE 기능을 사용하여 구현한다.
-	추천/비추천 : 다른 정보에 추천 및 비추천을 할 수 있다. UPDATE로 Information 테이블의 recommended, not_recommended를 수정한다.(추천 +1, 비추천+1)
-	신고 : 다른 유저를 신고할 수 있다. UPDATE로 user의 reported를 수정한다.
admin
-	정보 삭제 : reported가 일정 개수를 넘기면 해당 정보를 부적절하다고 판단해 삭제한다. 마찬가지로 cascade로 댓글까지 삭제한다.
-	회원 삭제 : 신고 횟수가 일정 개수를 넘긴 사용자를 DELETE로 삭제한다. Cascade로 삭제한다.
-	댓글 삭제 : reported가 일정 개수를 넘기면 해당 댓글을 부적절하다고 판단해 삭제한다.


##4.	데이터베이스 스키마 (Database schema)

User(user_id, username, password, email, , reported, role, created_at)
-	Primary key : user_id
-	Authorization: admin만이 정보를 수정 및 삭제할 수 있다.(reported 제외)
-	Reported는 타 사용자가 접근하여 신고를 할 수 있다.
Information(info_id, user_id, location, description, time, people_count, latitude, longitude, recommended, reported, created_at, updated_at)
-	Primary key: info_id
-	Foreign key: user_id-> User(user_id)
-	Authorization: 해당 정보를 작성한 user와 admin만이 정보를 수정할 수 있다.(recommended, not_recommanded 제외)
-	Authorization: recommended와 reported는 정보를 작성한 유저가 아닌 다른 유저만 수정할 수 있다.
Comment(comment_id, info_id, user_id, comment, created_at, updated_at, reported)
-	Primary key: comment_id
-	Foreign key: user_id-> User(user_id), info_id->Information(info_id)
-	Authorization: 해당 댓글을 작성한 user와 admin만이 정보를 수정할 수 있다.
