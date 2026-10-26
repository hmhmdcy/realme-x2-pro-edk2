from pathlib import Path
here=Path(__file__).resolve().parent
text=(here/'raw-dark-probe.cpp').read_text().replace('#include <linux/videodev2.h>','#include <linux/videodev2.h>\n#include <linux/media.h>\n#include <cstring>')
start=text.index('class PatternGuard {')
text=text[:start]+'''// Detach only the configured CSIPHY2 -> CSID0 data link for the known-input
// generator. Restore the exact saved flags after the generator is disabled.
class LinkGuard {
public:
    LinkGuard()
    {
        fd_ = open("/dev/media0", O_RDWR | O_CLOEXEC);
        require(fd_ >= 0, "open camera media graph");
        try {
            media_entity_desc entity{};
            unsigned int source = 0, sink = 0;
            for (entity.id = MEDIA_ENT_ID_FLAG_NEXT; ioctl(fd_, MEDIA_IOC_ENUM_ENTITIES, &entity) == 0; entity.id |= MEDIA_ENT_ID_FLAG_NEXT) {
                if (std::strcmp(entity.name, "msm_csiphy2") == 0) source = entity.id;
                if (std::strcmp(entity.name, "msm_csid0") == 0) sink = entity.id;
            }
            require(source && sink, "find exact CSIPHY2 and CSID0 entities");
            entity = {};
            entity.id = source;
            require(ioctl(fd_, MEDIA_IOC_ENUM_ENTITIES, &entity) == 0, "get CSIPHY2 entity");
            std::vector<media_pad_desc> pads(entity.pads);
            std::vector<media_link_desc> links(entity.links);
            media_links_enum enumeration{};
            enumeration.entity = source;
            enumeration.pads = pads.data();
            enumeration.links = links.data();
            require(ioctl(fd_, MEDIA_IOC_ENUM_LINKS, &enumeration) == 0, "read CSIPHY2 links");
            bool found = false;
            for (const auto &link : links) {
                if (link.source.entity == source && link.source.index == 1 && link.sink.entity == sink && link.sink.index == 0) {
                    require(!found, "unique configured data link");
                    saved_ = link;
                    found = true;
                }
            }
            require(found && (saved_.flags & MEDIA_LNK_FL_ENABLED) && !(saved_.flags & MEDIA_LNK_FL_IMMUTABLE), "configured link must be mutable and enabled");
            media_link_desc disabled = saved_;
            disabled.flags &= ~MEDIA_LNK_FL_ENABLED;
            require(ioctl(fd_, MEDIA_IOC_SETUP_LINK, &disabled) == 0, "detach physical input for CSID generator");
            detached_ = true;
        } catch (...) {
            close(fd_);
            fd_ = -1;
            throw;
        }
    }
    ~LinkGuard()
    {
        if (fd_ >= 0) {
            if (detached_ && ioctl(fd_, MEDIA_IOC_SETUP_LINK, &saved_) != 0)
                std::cerr << "ERROR: original CSIPHY2 link restore failed\\n";
            close(fd_);
        }
    }
private:
    int fd_ = -1;
    bool detached_ = false;
    media_link_desc saved_{};
};

''' + text[start:]
text=text.replace('(std::string(argv[3]) != "0" && std::string(argv[3]) != "2")', 'std::string(argv[3]) != "4"')
text=text.replace('    std::unique_ptr<PatternGuard> pattern;', '    std::unique_ptr<LinkGuard> link;\n    std::unique_ptr<PatternGuard> pattern;')
text=text.replace('        pattern = std::make_unique<PatternGuard>', '        link = std::make_unique<LinkGuard>();\n        pattern = std::make_unique<PatternGuard>')
text=text.replace('        pattern.reset();\n        capture->print();', '        pattern.reset();\n        link.reset();\n        capture->print();')
text=text.replace('    pattern.reset();\n    requests.clear();', '    pattern.reset();\n    link.reset();\n    requests.clear();')
(here/'csid-known-input-probe.cpp').write_text(text)
builder=(here/'build-raw-dark-probe.py').read_text().replace('raw-dark-probe','csid-known-input-probe').replace('raw10_dark_statistics_probe_built=True','csid_known_input_probe_built=True')
builder=builder.replace('uses_real_camera_sensor_camss_and_cpu_isp=True','uses_camss_csid_generator_and_cpu_isp=True,physical_sensor_not_a_positive_control=True,exact_csi_input_link_restored=True')
(here/'build-csid-probe.py').write_text(builder)
