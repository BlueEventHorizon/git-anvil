# Changelog

## [0.1.1] - 2026-10-29

### anvil

- **feat**: create-issue に `--repo [HOST/]OWNER/REPO` を追加。カレントリポジトリ（`origin`）と異なる起票先は、起票前に確認し、プレビューに作成先を表示する
- **feat**: commit / create-pr / create-issue の git・gh 操作を script にまとめ、`allowed-tools` を script の呼び出しに絞った。起動後の操作で許可の確認が出ない
- **feat**: PR 本文・Issue 本文・コミットメッセージを、`Write` で `.temp/anvil/<skill>/` に書いてから渡すようにした（引用符・バッククォート・`$` を含んでも壊れない）
- **feat**: create-issue で、内容がすでに会話にあるときは全項目の下書きをまとめて承認できるようにした
- **fix**: create-pr が CI を照会するリポジトリを、作成された PR の URL から取るようにした（fork で upstream に PR が作られた場合に、別リポジトリを照会していた）
- **fix**: gh に渡すリポジトリを、`github.com` でもホスト付き（`HOST/OWNER/REPO`）で渡すようにした（`GH_HOST` 等の既定ホストで別ホストと解釈されるのを防ぐ）
- **fix**: script のパスを引用符で囲み、空白を含む配置先でも実行できるようにした
- **fix**: commit が、`develop` / `main` / `master` のいずれにいても保護ブランチとして警告するようにした（create-pr と同じ判定）
- **fix**: commit のメッセージを、ステージ対象を確定した後に生成するようにした
- **破壊的変更**: `.git_information.yaml` を廃止した。ベースブランチは引数 → `develop` → `main` → `master` の順で決まる

### marketplace

- **chore**: anvil 0.1.1 のリリースに伴い marketplace バージョンをバンプ
