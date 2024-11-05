%bcond_with snapshot_build

%if %{with snapshot_build}
# Unlock LLVM Snapshot LUA functions
%{llvm_sb}
%endif

%global maj_ver 18
%global min_ver 1
%global libomp_version %{maj_ver}.%{min_ver}.8
#global rc_ver 4
%global libomp_srcdir openmp-%{libomp_version}%{?rc_ver:rc%{rc_ver}}.src
%global so_suffix %{maj_ver}.%{min_ver}

%if %{with snapshot_build}
%undefine rc_ver
%global maj_ver %{llvm_snapshot_version_major}
%global libomp_version %{llvm_snapshot_version}
%global so_suffix %{maj_ver}.%{min_ver}%{llvm_snapshot_version_suffix}
%endif

%global libomp_srcdir openmp-%{libomp_version}%{?rc_ver:rc%{rc_ver}}.src

%global toolchain clang

# Opt out of https://fedoraproject.org/wiki/Changes/fno-omit-frame-pointer
# https://bugzilla.redhat.com/show_bug.cgi?id=2158587
%undefine _include_frame_pointers

%ifarch ppc64le
%global libomp_arch ppc64
%else
%global libomp_arch %{_arch}
%endif

Name: libomp
Version: %{libomp_version}%{?rc_ver:~rc%{rc_ver}}%{?llvm_snapshot_version_suffix:~%{llvm_snapshot_version_suffix}}
Release: 1%{?dist}
Summary: OpenMP runtime for clang

License: NCSA
URL: http://openmp.llvm.org
%if %{with snapshot_build}
Source0: %{llvm_snapshot_source_prefix}openmp-%{llvm_snapshot_yyyymmdd}.src.tar.xz
%{llvm_snapshot_extra_source_tags}
%else
Source0: https://github.com/llvm/llvm-project/releases/download/llvmorg-%{libomp_version}%{?rc_ver:-rc%{rc_ver}}/%{libomp_srcdir}.tar.xz
Source1: https://github.com/llvm/llvm-project/releases/download/llvmorg-%{libomp_version}%{?rc_ver:-rc%{rc_ver}}/%{libomp_srcdir}.tar.xz.sig
Source2: release-keys.asc
%endif

BuildRequires: clang >= %{maj_ver}
# For clang-offload-packager
BuildRequires: clang-tools-extra
BuildRequires: cmake
BuildRequires: ninja-build
BuildRequires: elfutils-libelf-devel
BuildRequires: perl
BuildRequires: perl-Data-Dumper
BuildRequires: perl-Encode
BuildRequires: libffi-devel
# RHEL specific: libomp requires libterminfo
BuildRequires: ncurses-devel

# For gpg source verification
BuildRequires:	gnupg2

# libomptarget needs the llvm cmake files
BuildRequires: llvm-devel
BuildRequires: llvm-cmake-utils

Requires: elfutils-libelf%{?isa}

%description
OpenMP runtime for clang.

%package devel
Summary: OpenMP header files
Requires: %{name}%{?isa} = %{version}-%{release}
Requires: clang-resource-filesystem%{?isa} = %{version}

%description devel
OpenMP header files.

%prep
%if %{without snapshot_build}
%{gpgverify} --keyring='%{SOURCE2}' --signature='%{SOURCE1}' --data='%{SOURCE0}'
%endif
%autosetup -n %{libomp_srcdir} -p2

%build
%undefine __cmake_in_source_build

# LTO causes build failures in this package.  Disable LTO for now
# https://bugzilla.redhat.com/show_bug.cgi?id=1988155
%define _lto_cflags %{nil}

%cmake -GNinja \
	-DLIBOMP_INSTALL_ALIASES=OFF \
	-DCMAKE_MODULE_PATH=%{_datadir}/llvm/cmake/Modules \
	-DLLVM_DIR=%{_libdir}/cmake/llvm \
	-DCMAKE_INSTALL_INCLUDEDIR=%{_prefix}/lib/clang/%{maj_ver}/include \
%if 0%{?__isa_bits} == 64
	-DOPENMP_LIBDIR_SUFFIX=64 \
%else
	-DOPENMP_LIBDIR_SUFFIX= \
%endif
%if %{with snapshot_build}
	-DLLVM_VERSION_SUFFIX="%{llvm_snapshot_version_suffix}" \
%endif
	-DCMAKE_SKIP_RPATH:BOOL=ON

%cmake_build


%install
%cmake_install

# Remove static libraries with equivalent shared libraries
rm -rf %{buildroot}%{_libdir}/libarcher_static.a

%check
%cmake_build --target check-openmp || true

%files
%license LICENSE.TXT
%{_libdir}/libomp.so
%{_libdir}/libompd.so
%ifnarch %{arm}
%{_libdir}/libarcher.so
%endif
%ifnarch %{ix86} %{arm}
# libomptarget is not supported on 32-bit systems.
# s390x does not support the offloading plugins.
%ifnarch s390x
%{_libdir}/libomptarget.rtl.amdgpu.so.%{so_suffix}
%{_libdir}/libomptarget.rtl.cuda.so.%{so_suffix}
%{_libdir}/libomptarget.rtl.%{libomp_arch}.so.%{so_suffix}
%endif
%{_libdir}/libomptarget.so.%{so_suffix}
%endif

%files devel
%{_prefix}/lib/clang/%{maj_ver}/include/omp.h
%{_prefix}/lib/clang/%{maj_ver}/include/ompx.h
%ifnarch %{arm}
%{_prefix}/lib/clang/%{maj_ver}/include/omp-tools.h
%{_prefix}/lib/clang/%{maj_ver}/include/ompt.h
%{_prefix}/lib/clang/%{maj_ver}/include/ompt-multiplex.h
%endif
%{_libdir}/cmake/openmp/FindOpenMPTarget.cmake
%ifnarch %{ix86} %{arm}
# libomptarget is not supported on 32-bit systems.
# s390x does not support the offloading plugins.
%ifnarch s390x
%{_libdir}/libomptarget.rtl.amdgpu.so
%{_libdir}/libomptarget.rtl.cuda.so
%{_libdir}/libomptarget.rtl.%{libomp_arch}.so
%endif
%{_libdir}/libomptarget.devicertl.a
%{_libdir}/libomptarget-amdgpu-*.bc
%{_libdir}/libomptarget-nvptx-*.bc
%{_libdir}/libomptarget.so
%endif

%changelog
* Tue Jul 09 2024 Tom Stellard <tstellar@redhat.com> - 18.1.8-1
- 18.1.8 Release

* Fri Mar 22 2024 Tom Stellard <tstellar@redhat.com> - 18.1.2-1
- 18.1.2 Release

* Wed Mar 13 2024 Tom Stellard <tstellar@redhat.com> - 18.1.1-1
- 18.1.1 Release

* Thu Feb 29 2024 Tom Stellard <tstellar@redhat.com> - 18.1.0~rc4-1
- 18.1.0-rc4 Release

* Thu Jan 25 2024 Fedora Release Engineering <releng@fedoraproject.org> - 17.0.6-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

* Sun Jan 21 2024 Fedora Release Engineering <releng@fedoraproject.org> - 17.0.6-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

%{?llvm_snapshot_changelog_entry}

* Wed Nov 29 2023 Nikita Popov <npopov@redhat.com> - 17.0.6-1
- Update to LLVM 17.0.6

* Wed Oct 04 2023 Nikita Popov <npopov@redhat.com> - 17.0.2-1
- Update to LLVM 17.0.2

* Sat Jul 15 2023 Tom Stellard <tstellar@redhat.com> - 16.0.6-3
- Remove duplicated installed binaries

* Wed Jul 05 2023 Tom Stellard <tstellar@redhat.com> - 16.0.6-2
- Add explict libomp requres to libomp-devel

* Fri Jun 23 2023 Tom Stellard <tstellar@redhat.com> - 16.0.6-1
- 16.0.6 Release

* Fri Apr 28 2023 Tom Stellard <tstellar@redhat.com> - 16.0.0-1
- Release 16.0.0

* Thu Jan 19 2023 Tom Stellard <tstellar@redhat.com> - 15.0.7-1
- Update to LLVM 15.0.7

* Tue Sep 06 2022 Nikita Popov <npopov@redhat.com> - 15.0.0-1
- Update to LLVM 15.0.0

* Wed Aug 10 2022 Tom Stellard <tstellar@redhat.com> - 14.0.6-2
- Drop -test sub-package on i686

* Tue Jun 28 2022 Tom Stellard <tstellar@redhat.com> - 14.0.6-1
- 14.0.6 Release

* Wed May 18 2022 Timm Bäder <tbaeder@redhat.com> - 14.00-2
- Backport 40d3a0ba4d9e5452c0a68cfdaa8e88eb8ed5c63d to
  fix a strict aliasing issue.

* Thu Apr 07 2022 Timm Bäder <tbaeder@redhat.com> - 14.0.0-1
- Update to 14.0.0

* Thu Feb 03 2022 Tom Stellard <tstellar@redhat.com> - 13.0.1-1
- 13.0.1 Release

* Fri Oct 15 2021 Tom Stellard <tstellar@redhat.com> - 13.0.0-1
- 13.0.0 Release

* Fri Jul 16 2021 sguelton@redhat.com - 12.0.1-1
- 12.0.1 release

* Thu May 6 2021 sguelton@redhat.com - 12.0.0-1
- 12.0.0 release

* Thu Oct 29 2020 sguelton@redhat.com - 11.0.0-1
- 11.0.0 final release

* Mon Sep 21 2020 sguelton@redhat.com - 11.0.0-0.1.rc2
- 11.0.0-rc2 Release

* Fri Jul 24 2020 sguelton@redhat.com - 10.0.1-1
- 10.0.1 final

* Mon Jun 15 2020 sguelton@redhat.com - 10.0.0-2
- Better dependency specification, see rhbz#1841180

* Thu Apr 9 2020 sguelton@redhat.com - 10.0.0-1
- 10.0.0 final

* Thu Dec 19 2019 Tom Stellard <tstellar@redhat.com> - 9.0.1-1
- 9.0.1 Release

* Fri Sep 27 2019 Tom Stellard <tstellar@redhat.com> - 9.0.0-1
- 9.0.0 Release

* Thu Aug 1 2019 sguelton@redhat.com - 8.0.1-1
- 8.0.1 release

* Thu Jun 13 2019 sguelton@redhat.com - 8.0.1-0.1.rc2
- 8.0.1rc2 Release

* Mon Apr 29 2019 sguelton@redhat.com - 8.0.0-1
- 8.0.0 Release

* Fri Dec 14 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-1
- 7.0.1 Release

* Wed Dec 12 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-0.2.rc3
- Fix test failures on single-core systems

* Mon Dec 10 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-0.1.rc3
- 7.0.1-rc3 Release

* Tue Nov 27 2018 Tom Stellard <tstellar@redhat.com> - 7.0.0-1
- 7.0.0 Release

* Sat Nov 10 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-3
- Don't build libomp-test on i686

* Mon Oct 01 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-2
- Drop scl macros

* Wed Jul 11 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-1
- 6.0.1 Release

* Mon Jan 15 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-2
- Drop ExcludeArch: ppc64

* Thu Dec 21 2017 Tom Stellard <tstellar@redhat.com> - 5.0.1-1
- 5.0.1 Release.

* Wed Jun 21 2017 Tom Stellard <tstellar@redhat.com> - 4.0.1-1
- 4.0.1 Release.

* Wed Jun 07 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-3
- Rename libopenmp->libomp

* Fri May 26 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-2
- Disable build on s390x

* Mon May 15 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-1
- Initial version.
