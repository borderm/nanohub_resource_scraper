.mode tabs
.headers on
.output resource_report.tsv
select tag.tag, tag_link.resource_id, resource.title from tag
join tag_link on tag_link.tag_id = tag.id
join resource on resource.id = tag_link.resource_id;

.output tag_report.tsv
select tag, count(resource_id) from tag
join tag_link on tag_link.tag_id = tag.id
group by tag;