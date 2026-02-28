# Documentation de la base de données

Fichier : stash-go.sqlite

## Table `schema_migrations`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| version | uint64 | False | False | None |
| dirty | bool | False | False | None |


## Table `tags`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| name | varchar(255) | False | False | None |
| created_at | datetime | True | False | None |
| updated_at | datetime | True | False | None |
| ignore_auto_tag | boolean | True | False | '0' |
| description | TEXT | False | False | None |
| image_blob | varchar(255) | False | False | None |
| favorite | boolean | True | False | '0' |
| sort_name | varchar(255) | False | False | None |


## Table `sqlite_sequence`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| name |  | False | False | None |
| seq |  | False | False | None |


## Table `performer_stash_ids`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| performer_id | INTEGER | False | False | None |
| endpoint | varchar(255) | False | False | None |
| stash_id | varchar(36) | False | False | None |
| updated_at | datetime | True | False | '1970-01-01T00:00:00Z' |


## Table `studio_stash_ids`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| studio_id | INTEGER | False | False | None |
| endpoint | varchar(255) | False | False | None |
| stash_id | varchar(36) | False | False | None |
| updated_at | datetime | True | False | '1970-01-01T00:00:00Z' |


## Table `tags_relations`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| parent_id | INTEGER | False | True | None |
| child_id | INTEGER | False | True | None |


## Table `folders`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| path | varchar(255) | True | False | None |
| parent_folder_id | INTEGER | False | False | None |
| mod_time | datetime | True | False | None |
| created_at | datetime | True | False | None |
| updated_at | datetime | True | False | None |
| zip_file_id | INTEGER | False | False | None |


## Table `files`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| basename | varchar(255) | True | False | None |
| zip_file_id | INTEGER | False | False | None |
| parent_folder_id | INTEGER | True | False | None |
| size | INTEGER | True | False | None |
| mod_time | datetime | True | False | None |
| created_at | datetime | True | False | None |
| updated_at | datetime | True | False | None |


## Table `files_fingerprints`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| file_id | INTEGER | True | True | None |
| type | varchar(255) | True | True | None |
| fingerprint | BLOB | True | True | None |


## Table `video_files`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| file_id | INTEGER | True | True | None |
| duration | float | True | False | None |
| video_codec | varchar(255) | True | False | None |
| format | varchar(255) | True | False | None |
| audio_codec | varchar(255) | True | False | None |
| width | tinyint | True | False | None |
| height | tinyint | True | False | None |
| frame_rate | float | True | False | None |
| bit_rate | INTEGER | True | False | None |
| interactive | boolean | True | False | '0' |
| interactive_speed | INT | False | False | None |


## Table `video_captions`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| file_id | INTEGER | True | True | None |
| language_code | varchar(255) | True | True | None |
| filename | varchar(255) | True | False | None |
| caption_type | varchar(255) | True | True | None |


## Table `image_files`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| file_id | INTEGER | True | True | None |
| format | varchar(255) | True | False | None |
| width | tinyint | True | False | None |
| height | tinyint | True | False | None |


## Table `images_files`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| image_id | INTEGER | True | True | None |
| file_id | INTEGER | True | True | None |
| primary | boolean | True | False | None |


## Table `galleries_files`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| gallery_id | INTEGER | True | True | None |
| file_id | INTEGER | True | True | None |
| primary | boolean | True | False | None |


## Table `scenes_files`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| scene_id | INTEGER | True | True | None |
| file_id | INTEGER | True | True | None |
| primary | boolean | True | False | None |


## Table `performers_scenes`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| performer_id | INTEGER | False | True | None |
| scene_id | INTEGER | False | True | None |


## Table `scene_markers_tags`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| scene_marker_id | INTEGER | False | True | None |
| tag_id | INTEGER | False | True | None |


## Table `scenes_tags`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| scene_id | INTEGER | False | True | None |
| tag_id | INTEGER | False | True | None |


## Table `groups_scenes`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| group_id | INTEGER | False | True | None |
| scene_id | INTEGER | False | True | None |
| scene_index | tinyint | False | False | None |


## Table `performers_images`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| performer_id | INTEGER | False | True | None |
| image_id | INTEGER | False | True | None |


## Table `images_tags`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| image_id | INTEGER | False | True | None |
| tag_id | INTEGER | False | True | None |


## Table `scene_stash_ids`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| scene_id | INTEGER | True | True | None |
| endpoint | varchar(255) | True | True | None |
| stash_id | varchar(36) | True | False | None |
| updated_at | datetime | True | False | '1970-01-01T00:00:00Z' |


## Table `scenes_galleries`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| scene_id | INTEGER | True | True | None |
| gallery_id | INTEGER | True | True | None |


## Table `galleries_images`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| gallery_id | INTEGER | True | True | None |
| image_id | INTEGER | True | True | None |
| cover | BOOLEAN | True | False | 0 |


## Table `performers_galleries`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| performer_id | INTEGER | True | True | None |
| gallery_id | INTEGER | True | True | None |


## Table `galleries_tags`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| gallery_id | INTEGER | True | True | None |
| tag_id | INTEGER | True | True | None |


## Table `performers_tags`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| performer_id | INTEGER | True | True | None |
| tag_id | INTEGER | True | True | None |


## Table `tag_aliases`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| tag_id | INTEGER | True | True | None |
| alias | varchar(255) | True | True | None |


## Table `studio_aliases`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| studio_id | INTEGER | True | True | None |
| alias | varchar(255) | True | True | None |


## Table `performer_aliases`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| performer_id | INTEGER | True | True | None |
| alias | varchar(255) | True | True | None |


## Table `galleries_chapters`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| title | varchar(255) | True | False | None |
| image_index | INTEGER | True | False | None |
| gallery_id | INTEGER | True | False | None |
| created_at | datetime | True | False | None |
| updated_at | datetime | True | False | None |


## Table `blobs`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| checksum | varchar(255) | True | True | None |
| blob | BLOB | False | False | None |


## Table `scene_urls`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| scene_id | INTEGER | True | True | None |
| position | INTEGER | True | True | None |
| url | varchar(255) | True | True | None |


## Table `scene_markers`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| title | VARCHAR(255) | True | False | None |
| seconds | FLOAT | True | False | None |
| primary_tag_id | INTEGER | True | False | None |
| scene_id | INTEGER | True | False | None |
| created_at | DATETIME | True | False | None |
| updated_at | DATETIME | True | False | None |
| end_seconds | FLOAT | False | False | None |


## Table `studios`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| name | VARCHAR(255) | True | False | None |
| parent_id | INTEGER | False | False | NULL |
| created_at | DATETIME | True | False | None |
| updated_at | DATETIME | True | False | None |
| details | TEXT | False | False | None |
| rating | TINYINT | False | False | None |
| ignore_auto_tag | BOOLEAN | True | False | FALSE |
| image_blob | VARCHAR(255) | False | False | None |
| favorite | boolean | True | False | '0' |


## Table `saved_filters`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| name | varchar(510) | True | False | None |
| mode | varchar(255) | True | False | None |
| find_filter | BLOB | False | False | None |
| object_filter | BLOB | False | False | None |
| ui_options | BLOB | False | False | None |


## Table `image_urls`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| image_id | INTEGER | True | True | None |
| position | INTEGER | True | True | None |
| url | varchar(255) | True | True | None |


## Table `images`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| title | varchar(255) | False | False | None |
| rating | tinyint | False | False | None |
| studio_id | INTEGER | False | False | None |
| o_counter | tinyint | True | False | 0 |
| organized | boolean | True | False | '0' |
| created_at | datetime | True | False | None |
| updated_at | datetime | True | False | None |
| date | date | False | False | None |
| code | TEXT | False | False | None |
| photographer | TEXT | False | False | None |
| details | TEXT | False | False | None |
| date_precision | TINYINT | False | False | None |


## Table `gallery_urls`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| gallery_id | INTEGER | True | True | None |
| position | INTEGER | True | True | None |
| url | varchar(255) | True | True | None |


## Table `galleries`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| folder_id | INTEGER | False | False | None |
| title | varchar(255) | False | False | None |
| date | date | False | False | None |
| details | TEXT | False | False | None |
| studio_id | INTEGER | False | False | None |
| rating | tinyint | False | False | None |
| organized | boolean | True | False | '0' |
| created_at | datetime | True | False | None |
| updated_at | datetime | True | False | None |
| code | TEXT | False | False | None |
| photographer | TEXT | False | False | None |
| date_precision | TINYINT | False | False | None |


## Table `scenes`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| title | varchar(255) | False | False | None |
| details | TEXT | False | False | None |
| date | date | False | False | None |
| rating | tinyint | False | False | None |
| studio_id | INTEGER | False | False | None |
| organized | boolean | True | False | '0' |
| created_at | datetime | True | False | None |
| updated_at | datetime | True | False | None |
| code | TEXT | False | False | None |
| director | TEXT | False | False | None |
| resume_time | float | True | False | 0 |
| play_duration | float | True | False | 0 |
| cover_blob | varchar(255) | False | False | None |
| date_precision | TINYINT | False | False | None |


## Table `group_urls`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| group_id | INTEGER | True | True | None |
| position | INTEGER | True | True | None |
| url | varchar(255) | True | True | None |


## Table `groups`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| name | varchar(255) | True | False | None |
| aliases | varchar(255) | False | False | None |
| duration | INTEGER | False | False | None |
| date | date | False | False | None |
| rating | tinyint | False | False | None |
| studio_id | INTEGER | False | False | None |
| director | varchar(255) | False | False | None |
| description | TEXT | False | False | None |
| created_at | datetime | True | False | None |
| updated_at | datetime | True | False | None |
| front_image_blob | varchar(255) | False | False | None |
| back_image_blob | varchar(255) | False | False | None |
| date_precision | TINYINT | False | False | None |


## Table `groups_tags`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| group_id | INTEGER | True | True | None |
| tag_id | INTEGER | True | True | None |


## Table `performer_urls`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| performer_id | INTEGER | True | True | None |
| position | INTEGER | True | True | None |
| url | varchar(255) | True | True | None |


## Table `performers`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| id | INTEGER | True | True | None |
| name | varchar(255) | True | False | None |
| disambiguation | varchar(255) | False | False | None |
| gender | varchar(20) | False | False | None |
| birthdate | date | False | False | None |
| ethnicity | varchar(255) | False | False | None |
| country | varchar(255) | False | False | None |
| eye_color | varchar(255) | False | False | None |
| height | INT | False | False | None |
| measurements | varchar(255) | False | False | None |
| fake_tits | varchar(255) | False | False | None |
| career_length | varchar(255) | False | False | None |
| tattoos | varchar(255) | False | False | None |
| piercings | varchar(255) | False | False | None |
| favorite | boolean | True | False | '0' |
| created_at | datetime | True | False | None |
| updated_at | datetime | True | False | None |
| details | TEXT | False | False | None |
| death_date | date | False | False | None |
| hair_color | varchar(255) | False | False | None |
| weight | INTEGER | False | False | None |
| rating | tinyint | False | False | None |
| ignore_auto_tag | boolean | True | False | '0' |
| image_blob | varchar(255) | False | False | None |
| penis_length | float | False | False | None |
| circumcised | varchar[10] | False | False | None |
| birthdate_precision | TINYINT | False | False | None |
| death_date_precision | TINYINT | False | False | None |


## Table `studios_tags`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| studio_id | INTEGER | True | True | None |
| tag_id | INTEGER | True | True | None |


## Table `scenes_view_dates`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| scene_id | INTEGER | True | False | None |
| view_date | datetime | True | False | None |


## Table `scenes_o_dates`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| scene_id | INTEGER | True | False | None |
| o_date | datetime | True | False | None |


## Table `groups_relations`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| containing_id | INTEGER | True | True | None |
| sub_id | INTEGER | True | True | None |
| order_index | INTEGER | True | False | None |
| description | varchar(255) | False | False | None |


## Table `performer_custom_fields`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| performer_id | INTEGER | True | True | None |
| field | varchar(64) | True | True | None |
| value | BLOB | True | False | None |


## Table `studio_urls`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| studio_id | INTEGER | True | True | None |
| position | INTEGER | True | True | None |
| url | varchar(255) | True | True | None |


## Table `tag_stash_ids`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| tag_id | INTEGER | False | False | None |
| endpoint | varchar(255) | False | False | None |
| stash_id | varchar(36) | False | False | None |
| updated_at | datetime | True | False | '1970-01-01T00:00:00Z' |


## Table `sqlite_stat1`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| tbl |  | False | False | None |
| idx |  | False | False | None |
| stat |  | False | False | None |


## Table `sqlite_stat4`

| Champ | Type | Not Null | Clé primaire | Valeur défaut |
|------|------|---------|--------------|----------------|
| tbl |  | False | False | None |
| idx |  | False | False | None |
| neq |  | False | False | None |
| nlt |  | False | False | None |
| ndlt |  | False | False | None |
| sample |  | False | False | None |

