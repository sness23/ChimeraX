# vim: set expandtab shiftwidth=4 softtabstop=4:

# === UCSF ChimeraX Copyright ===
# Copyright 2016 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  For details see:
# http://www.rbvi.ucsf.edu/chimerax/docs/licensing.html
# This notice must be embedded in or attached to all copies,
# including partial copies, of the software or any revisions
# or derivations thereof.
# === UCSF ChimeraX Copyright ===

# Session save/restore of graphics state

class ViewState:

    version = 1
    save_attrs = ['camera', 'lighting', 'material',
                  'center_of_rotation', 'center_of_rotation_method', 'background_color']
    silhouette_attrs = ['enabled', 'thickness', 'color', 'depth_jump']

    @staticmethod
    def take_snapshot(view, session, flags):
        v = view
        data = {a:getattr(v,a) for a in ViewState.save_attrs}

        # TODO: Handle cameras other than MonoCamera
        c = v.camera
        from . import MonoCamera, OrthographicCamera
        if not isinstance(c, (MonoCamera, OrthographicCamera)):
            p = c.position
            c = MonoCamera()
            c.position = p
            data['camera'] = c

        data['silhouettes'] = {attr:getattr(v.render.silhouette, attr) for attr in ViewState.silhouette_attrs}
        data['window_size'] = v.window_size
        data['clip_planes'] = v.clip_planes.planes()
        data['version'] = ViewState.version
        return data

    @staticmethod
    def restore_snapshot(session, data):
        # Restores session.main_view
        v = session.main_view
        ViewState.set_state_from_snapshot(v, session, data)
        return v

    @staticmethod
    def set_state_from_snapshot(view, session, data):
        v = view
        for k in ViewState.save_attrs:
            if k in data:
                setattr(v, k, data[k])

        # Root drawing has redraw callback set to None -- fix it.
        v.drawing.set_redraw_callback(v._drawing_manager)

        # Restore clip planes
        v.clip_planes.replace_planes(data['clip_planes'])

        # Restore window size
        resize = session.restore_options.get('resize window')
        if resize is None:
            from ..core_settings import settings
            resize = settings.resize_window_on_session_restore
        if resize:
            ui = session.ui
            maximized = (ui.is_gui and ui.main_window.window_maximized())
            if maximized:
                resize = False
        if resize:
            from .windowsize import window_size
            width, height = data['window_size']
            window_size(session, width, height)

        if 'silhouettes' in data:
            for attr, value in data['silhouettes'].items():
                setattr(v.render.silhouette, attr, value)

    @staticmethod
    def reset_state(view, session):
        pass


class CameraState:

    version = 1
    save_attrs = ['name', 'position', 'field_of_view', 'field_width']

    @staticmethod
    def take_snapshot(camera, session, flags):
        c = camera
        from .camera import MonoCamera, OrthographicCamera
        if isinstance(c, (MonoCamera, OrthographicCamera)):
            data = {a:getattr(c,a) for a in CameraState.save_attrs if hasattr(c,a)}
        else:
            # TODO: Restore other camera modes.
            session.logger.info('"%s" camera settings not currently saved in sessions' % c.name)
            data = {'position': c.position}
        data['version'] = CameraState.version
        return data

    @staticmethod
    def restore_snapshot(session, data):
        cname = data.get('name', 'mono')
        from .camera import MonoCamera, OrthographicCamera
        if cname == 'mono':
            c = MonoCamera()
        elif cname == 'orthographic':
            c = OrthographicCamera()
        else:
            c = MonoCamera()
        CameraState.set_state_from_snapshot(c, session, data)
        return c

    @staticmethod
    def set_state_from_snapshot(camera, session, data):
        for k in CameraState.save_attrs:
            if k in data:
                setattr(camera, k, data[k])

    @staticmethod
    def reset_state(camera, session):
        pass


class LightingState:

    version = 1
    save_attrs = [
        'key_light_direction',
        'key_light_color',
        'key_light_intensity',
        'fill_light_direction',
        'fill_light_color',
        'fill_light_intensity',
        'ambient_light_color',
        'ambient_light_intensity',
        'depth_cue',
        'depth_cue_start',
        'depth_cue_end',
        'depth_cue_color',
        'move_lights_with_camera',
        'shadows',
        'shadow_map_size',
        'shadow_depth_bias',
        'multishadow',
        'multishadow_map_size',
        'multishadow_depth_bias',
        ]

    @staticmethod
    def take_snapshot(lighting, session, flags):
        l = lighting
        data = {a:getattr(l,a) for a in LightingState.save_attrs}
        data['version'] = LightingState.version
        return data

    @staticmethod
    def restore_snapshot(session, data):
        from . import Lighting
        l = Lighting()
        LightingState.set_state_from_snapshot(l, session, data)
        return l

    @staticmethod
    def set_state_from_snapshot(lighting, session, data):
        l = lighting
        for k in LightingState.save_attrs:
            if k in data:
                setattr(l, k, data[k])

    @staticmethod
    def reset_state(lighting, session):
        pass


class MaterialState:

    version = 1
    save_attrs = [
        'ambient_reflectivity',
        'diffuse_reflectivity',
        'specular_reflectivity',
        'specular_exponent',
        ]

    @staticmethod
    def take_snapshot(material, session, flags):
        m = material
        data = {a:getattr(m,a) for a in MaterialState.save_attrs}
        data['version'] = MaterialState.version
        return data

    @staticmethod
    def restore_snapshot(session, data):
        from . import Material
        m = Material()
        MaterialState.set_state_from_snapshot(m, session, data)
        return m

    @staticmethod
    def set_state_from_snapshot(material, session, data):
        m = material
        for k in MaterialState.save_attrs:
            if k in data:
                setattr(m, k, data[k])

    @staticmethod
    def reset_state(Material, session):
        pass


class ClipPlaneState:

    version = 1
    save_attrs = [
        'name',
        'normal',
        'plane_point',
        'camera_normal',
    ]

    @staticmethod
    def take_snapshot(clip_plane, session, flags):
        cp = clip_plane
        data = {a:getattr(cp,a) for a in ClipPlaneState.save_attrs}
        data['version'] = ClipPlaneState.version
        return data

    @staticmethod
    def restore_snapshot(session, data):
        from . import ClipPlane
        cp = ClipPlane(data['name'], data['normal'], data['plane_point'], data['camera_normal'])
        return cp

    @staticmethod
    def reset_state(clip_plane, session):
        pass


class DrawingState:

    version = 1
    save_attrs = ['name', 'vertices', 'triangles', 'normals', 'vertex_colors', 
                  'triangle_mask', 'edge_mask', 'display_style', 'texture', 
                  'ambient_texture', 'ambient_texture_transform', 
                  'use_lighting', 'positions', 'display_positions', 
                  'highlighted_positions', 'highlighted_triangles_mask', 'colors']

    @staticmethod
    def take_snapshot(drawing, session, flags):
        d = drawing
        data = {a:getattr(d,a) for a in DrawingState.save_attrs}
        data['children'] = d.child_drawings()
        data['version'] = DrawingState.version
        return data

    @staticmethod
    def restore_snapshot(session, data):
        d = Drawing('')
        DrawingState.set_state_from_stanpshot(d, session, data)
        return d

    @staticmethod
    def set_state_from_snapshot(drawing, session, data):
        d = drawing
        for k in DrawingState.save_attrs:
            if k in data:
                setattr(d, k, data[k])
        for c in data['children']:
            d.add_drawing(c)

    @staticmethod
    def reset_state(drawing, session):
        pass
