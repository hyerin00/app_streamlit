import pandas as pd
import requests
import time

# ✅ CSV 파일 로드
df = pd.read_csv("C:/Users/USER/붕붕/car/sleep.csv", encoding="utf-8")  # 인코딩 확인 완료

# ✅ Kakao REST API 키 입력
KAKAO_API_KEY = "a78b007077267046a877cead1e83d84c"

# ✅ 주소 → 위도/경도 변환 함수
def get_coords_kakao(address):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address}
    res = requests.get(url, headers=headers, params=params)

    if res.status_code == 200:
        result = res.json()["documents"]
        if result:
            return result[0]["y"], result[0]["x"]  # 위도, 경도
    return None, None

# ✅ 지오코딩 수행
df["위도"], df["경도"] = zip(*df["adress"].map(lambda x: get_coords_kakao(str(x)) if pd.notnull(x) else (None, None)))
time.sleep(0.3)  # 너무 빠른 요청 방지

# ✅ 결과 저장
df.to_csv("slepp_end_geocoded.csv", encoding="utf-8", index=False)
print("📍 주소 → 좌표 변환 완료! 파일 저장됨: slepp_end_geocoded.csv")
