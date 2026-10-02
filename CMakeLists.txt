if(CONFIG_ZMK_HIRES_DIAL)
  # The pinned dial module uses ZMK behavior headers without exporting this path.
  zephyr_include_directories(${APPLICATION_SOURCE_DIR}/include)
  # Adapt the upstream dial API name to the pinned cormoran ZMK endpoint API.
  zephyr_compile_definitions(zmk_endpoints_selected=zmk_endpoint_get_selected)
endif()

if(CONFIG_EQUINOX_PAT_DIAGNOSTICS)
  zephyr_library()
  zephyr_library_sources(src/pat_diagnostics.c)
endif()
if(CONFIG_EQUINOX_PMW_DIAGNOSTICS)
  zephyr_library()
  zephyr_library_include_directories(${APPLICATION_SOURCE_DIR}/include)
  zephyr_library_sources(src/pmw_diagnostics.c)
endif()
