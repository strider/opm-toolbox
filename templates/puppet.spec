%{!?upstream_version: %global upstream_version %{version}%{?milestone}}
{% if metadata.from_puppetlabs -%}
%%define upstream_name {{ metadata.project_name }}
{% endif %}
Name:                   {{ metadata.name }}
Version:                XXX
Release:                XXX
Summary:                {{ metadata.summary }}
License:                {{ metadata.license }}

URL:                    {{ metadata.project_page }}

Source0:                {{ metadata.source0 }}

BuildArch:              noarch

{% for dep in metadata.dependencies -%}
Requires:               {{ dep.name }}
{% endfor %}
Requires:               puppet >= 2.7.0

%description
{{ metadata.description }}

%prep
{% if 'openstack.org' in metadata.source0 -%}
%setup -q -n openstack-{{ metadata.project }}-%{upstream_version}
{% else -%}
%setup -q -n {{ '%{'+metadata.upstream_name+'}-%{upstream_version}' }}
{%- endif %}

find . -type f -name ".*" -exec rm {} +
find . -size 0 -exec rm {} +
find . \( -name "*.pl" -o -name "*.sh"  \) -exec chmod +x {} +
find . \( -name "*.pp" -o -name "*.py"  \) -exec chmod -x {} +
find . \( -name "*.rb" -o -name "*.erb" \) -exec chmod -x {} +
find . \( -name spec -o -name ext \) | xargs rm -rf

%build


%install
install -d -m 0755 %{buildroot}/%{_datadir}/openstack-puppet/modules/{{ metadata.project }}/
cp -rp * %{buildroot}/%{_datadir}/openstack-puppet/modules/{{ metadata.project }}/
{% if "nova" == metadata.project -%}
rm -f %{buildroot}/%{_datadir}/openstack-puppet/modules/nova/files/nova-novncproxy.init
{%- endif %}


%files
%{_datadir}/openstack-puppet/modules/{{ metadata.project }}/


%changelog

