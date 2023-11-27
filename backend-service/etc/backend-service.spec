Name: backend-service
Version: %{getenv:CI_COMMIT_TAG}
Release: 1%{?dist}
Summary: Backend service rpm

License: MIT
URL: http://devops.telekom.de
Source: %{name}-%{version}.tar.gz

%description
This is an empty package.

%prep
# No preparation needed for an empty package

%build
# No build steps needed for an empty package

%install
# No installation steps needed for an empty package
mkdir -p %{buildroot}

%files
# No files to include for an empty package

%changelog
# No changelog entries for an empty package
