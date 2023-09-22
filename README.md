# JobcanAuto
## 機能について
ジョブカンの工数入力を自動で行います。  
あらかじめジョブカン工数かんたん入力設定でテンプレートを作成する必要があります。  
テンプレートの1番目を選択し、作業時間と同じ時間を工数に入力するという作業を営業日数繰り返します。  


#### 注意  
・テンプレートがない場合動作しません。  
・テンプレート1番に複数の項目がある場合、No1のみ時間が入力されます。  
・土日祝は無視されます。

## Install Package

```
pip install selenium  
pip install jpholiday
```

## config.json
```
{
    "id": "Digicom.Taro@digital-com.com",
    "pass": "MyPassword",
    "months_ago": 0
}
```
・ id : ジョブカンのログインIDです。  
・ pass : ジョブカンのログインパスワードです。  
・  months_ago : 何か月前の情報を入力するかの数値です。  月をまたいでしまった場合に1等の数値を入れます。

## chromedriver
googlechromeを動かすのに必要です。  
定期的にアップデートされる為、動かなくなったら更新する必要があります。

参考サイト  
https://googlechromelabs.github.io/chrome-for-testing/  
https://chromedriver.chromium.org/downloads

