-- =====================================================================
-- PROYECTO : Sistema de servicios de aseo en viviendas (LimpiaHogar)
-- MOTOR    : PostgreSQL (ejecutar en el Query Tool de pgAdmin 4)
-- ORIGEN   : Modelo lógico UML (24 tablas)
-- NOTACIÓN : # = clave primaria, * = clave foránea
--
-- Antes de ejecutar: crea la base de datos (por ejemplo "aseo_viviendas")
-- desde pgAdmin, ábrela y luego ejecuta este script en su Query Tool.
-- =====================================================================


-- =====================================================================
-- 1. TABLAS QUE NO DEPENDEN DE OTRAS (catálogos y entidades base)
-- =====================================================================

CREATE TABLE zona (
    id_zona             INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(50)  NOT NULL,
    CONSTRAINT pk_zona        PRIMARY KEY (id_zona),
    CONSTRAINT uq_zona_nombre UNIQUE (nombre)
);

CREATE TABLE tipo_vivienda (
    id_tipo_vivienda    INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(50)  NOT NULL,
    CONSTRAINT pk_tipo_vivienda        PRIMARY KEY (id_tipo_vivienda),
    CONSTRAINT uq_tipo_vivienda_nombre UNIQUE (nombre)
);

CREATE TABLE tipo_area (
    id_tipo_area        INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(50)  NOT NULL,
    CONSTRAINT pk_tipo_area        PRIMARY KEY (id_tipo_area),
    CONSTRAINT uq_tipo_area_nombre UNIQUE (nombre)
);

CREATE TABLE tipo_elemento (
    id_tipo_elemento    INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(50)  NOT NULL,
    CONSTRAINT pk_tipo_elemento        PRIMARY KEY (id_tipo_elemento),
    CONSTRAINT uq_tipo_elemento_nombre UNIQUE (nombre)
);

CREATE TABLE cliente (
    id_cliente          INTEGER GENERATED ALWAYS AS IDENTITY,
    documento           VARCHAR(20)  NOT NULL,
    nombre              VARCHAR(60)  NOT NULL,
    apellido            VARCHAR(60)  NOT NULL,
    telefono            VARCHAR(15)  NOT NULL,
    correo              VARCHAR(100),
    estado              VARCHAR(10)  NOT NULL DEFAULT 'activo',
    CONSTRAINT pk_cliente           PRIMARY KEY (id_cliente),
    CONSTRAINT uq_cliente_documento UNIQUE (documento),
    CONSTRAINT uq_cliente_correo    UNIQUE (correo),
    CONSTRAINT ck_cliente_estado    CHECK (estado IN ('activo', 'bloqueado'))
);

CREATE TABLE empleado (
    id_empleado         INTEGER GENERATED ALWAYS AS IDENTITY,
    documento           VARCHAR(20)  NOT NULL,
    nombre              VARCHAR(60)  NOT NULL,
    apellido            VARCHAR(60)  NOT NULL,
    telefono            VARCHAR(15)  NOT NULL,
    estado              VARCHAR(10)  NOT NULL DEFAULT 'activo',
    id_supervisor       INTEGER,                 -- * (auto-relación, opcional 0..1)
    CONSTRAINT pk_empleado             PRIMARY KEY (id_empleado),
    CONSTRAINT uq_empleado_documento   UNIQUE (documento),
    CONSTRAINT ck_empleado_estado      CHECK (estado IN ('activo', 'inactivo')),
    CONSTRAINT ck_empleado_supervisor  CHECK (id_supervisor IS NULL OR id_supervisor <> id_empleado)
);

CREATE TABLE especialidad (
    id_especialidad     INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(60)  NOT NULL,
    CONSTRAINT pk_especialidad        PRIMARY KEY (id_especialidad),
    CONSTRAINT uq_especialidad_nombre UNIQUE (nombre)
);

CREATE TABLE categoria_insumo (
    id_categoria        INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(30)  NOT NULL,
    CONSTRAINT pk_categoria_insumo     PRIMARY KEY (id_categoria),
    CONSTRAINT uq_categoria_insumo_nom UNIQUE (nombre),
    CONSTRAINT ck_categoria_insumo_nom CHECK (nombre IN ('producto', 'utensilio', 'herramienta'))
);

CREATE TABLE proveedor (
    id_proveedor        INTEGER GENERATED ALWAYS AS IDENTITY,
    nit                 VARCHAR(20)  NOT NULL,
    nombre              VARCHAR(100) NOT NULL,
    telefono            VARCHAR(15),
    CONSTRAINT pk_proveedor     PRIMARY KEY (id_proveedor),
    CONSTRAINT uq_proveedor_nit UNIQUE (nit)
);

CREATE TABLE metodo_pago (
    id_metodo_pago      INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(40)  NOT NULL,
    CONSTRAINT pk_metodo_pago        PRIMARY KEY (id_metodo_pago),
    CONSTRAINT uq_metodo_pago_nombre UNIQUE (nombre)
);


-- =====================================================================
-- 2. TABLAS CON DEPENDENCIAS (las FK se agregan en la sección 4)
-- =====================================================================

CREATE TABLE barrio (
    id_barrio           INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(60)  NOT NULL,
    id_zona             INTEGER      NOT NULL,   -- *
    CONSTRAINT pk_barrio             PRIMARY KEY (id_barrio),
    CONSTRAINT uq_barrio_nombre_zona UNIQUE (nombre, id_zona)
);

CREATE TABLE vivienda (
    id_vivienda         INTEGER GENERATED ALWAYS AS IDENTITY,
    id_cliente          INTEGER      NOT NULL,   -- *
    id_barrio           INTEGER      NOT NULL,   -- *
    id_tipo_vivienda    INTEGER      NOT NULL,   -- *
    direccion           VARCHAR(120) NOT NULL,
    CONSTRAINT pk_vivienda PRIMARY KEY (id_vivienda)
);

CREATE TABLE area (
    id_area             INTEGER GENERATED ALWAYS AS IDENTITY,
    id_vivienda         INTEGER      NOT NULL,   -- *
    id_tipo_area        INTEGER      NOT NULL,   -- *
    descripcion         VARCHAR(100),
    CONSTRAINT pk_area PRIMARY KEY (id_area)
);

CREATE TABLE elemento (
    id_elemento         INTEGER GENERATED ALWAYS AS IDENTITY,
    id_area             INTEGER      NOT NULL,   -- *
    id_tipo_elemento    INTEGER      NOT NULL,   -- *
    descripcion         VARCHAR(100),
    CONSTRAINT pk_elemento PRIMARY KEY (id_elemento)
);

CREATE TABLE tipo_servicio (
    id_tipo_servicio    INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(80)  NOT NULL,
    duracion_horas      NUMERIC(4,1) NOT NULL,
    precio              NUMERIC(10,2) NOT NULL,
    id_especialidad     INTEGER      NOT NULL,   -- *
    CONSTRAINT pk_tipo_servicio          PRIMARY KEY (id_tipo_servicio),
    CONSTRAINT uq_tipo_servicio_nombre   UNIQUE (nombre),
    CONSTRAINT ck_tipo_servicio_duracion CHECK (duracion_horas > 0),
    CONSTRAINT ck_tipo_servicio_precio   CHECK (precio >= 0)
);

CREATE TABLE servicio (
    id_servicio           INTEGER GENERATED ALWAYS AS IDENTITY,
    id_vivienda           INTEGER     NOT NULL,  -- *
    fecha                 DATE        NOT NULL,
    hora_inicio           TIME        NOT NULL,
    estado                VARCHAR(12) NOT NULL DEFAULT 'pendiente',
    observaciones         TEXT,
    calificacion_servicio SMALLINT,
    comentario_servicio   TEXT,
    CONSTRAINT pk_servicio              PRIMARY KEY (id_servicio),
    CONSTRAINT ck_servicio_estado       CHECK (estado IN ('pendiente', 'confirmado', 'finalizado', 'cancelado')),
    CONSTRAINT ck_servicio_calificacion CHECK (calificacion_servicio BETWEEN 1 AND 5),
    -- Supuesto 12: solo se califica un servicio finalizado
    CONSTRAINT ck_servicio_calif_final  CHECK (calificacion_servicio IS NULL OR estado = 'finalizado')
);

CREATE TABLE detalle_servicio (
    id_detalle          INTEGER GENERATED ALWAYS AS IDENTITY,
    id_servicio         INTEGER       NOT NULL,  -- *
    id_tipo_servicio    INTEGER       NOT NULL,  -- *
    id_area             INTEGER,                 -- * opcional (0..1)
    id_elemento         INTEGER,                 -- * opcional (0..1)
    precio_aplicado     NUMERIC(10,2) NOT NULL,
    CONSTRAINT pk_detalle_servicio        PRIMARY KEY (id_detalle),
    CONSTRAINT ck_detalle_servicio_precio CHECK (precio_aplicado >= 0),
    -- Supuesto 5: el servicio aplica a toda la vivienda (ambos NULL),
    -- a un área (solo id_area) o a un elemento (solo id_elemento)
    CONSTRAINT ck_detalle_servicio_alcance CHECK (id_area IS NULL OR id_elemento IS NULL)
);

CREATE TABLE insumo (
    id_insumo           INTEGER GENERATED ALWAYS AS IDENTITY,
    nombre              VARCHAR(80)  NOT NULL,
    id_categoria        INTEGER      NOT NULL,   -- *
    id_proveedor        INTEGER      NOT NULL,   -- *
    stock               INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT pk_insumo        PRIMARY KEY (id_insumo),
    CONSTRAINT uq_insumo_nombre UNIQUE (nombre),
    CONSTRAINT ck_insumo_stock  CHECK (stock >= 0)
);

CREATE TABLE pago (
    id_pago             INTEGER GENERATED ALWAYS AS IDENTITY,
    id_servicio         INTEGER       NOT NULL,  -- * (relación 1:1)
    id_metodo_pago      INTEGER       NOT NULL,  -- *
    fecha               DATE          NOT NULL DEFAULT CURRENT_DATE,
    monto               NUMERIC(10,2) NOT NULL,
    CONSTRAINT pk_pago          PRIMARY KEY (id_pago),
    CONSTRAINT uq_pago_servicio UNIQUE (id_servicio),   -- un solo pago por servicio
    CONSTRAINT ck_pago_monto    CHECK (monto > 0)
);


-- =====================================================================
-- 3. TABLAS INTERMEDIAS (relaciones N:M)
-- =====================================================================

-- Empleado N:M Especialidad
CREATE TABLE empleado_especialidad (
    id_empleado         INTEGER NOT NULL,        -- #*
    id_especialidad     INTEGER NOT NULL,        -- #*
    CONSTRAINT pk_empleado_especialidad PRIMARY KEY (id_empleado, id_especialidad)
);

-- Empleado N:M Zona
CREATE TABLE empleado_zona (
    id_empleado         INTEGER NOT NULL,        -- #*
    id_zona             INTEGER NOT NULL,        -- #*
    CONSTRAINT pk_empleado_zona PRIMARY KEY (id_empleado, id_zona)
);

-- Servicio N:M Empleado (con las calificaciones como atributos de la relación)
CREATE TABLE asignacion (
    id_servicio           INTEGER  NOT NULL,     -- #*
    id_empleado           INTEGER  NOT NULL,     -- #*
    calificacion_empleado SMALLINT,              -- la que da el cliente al empleado
    comentario_empleado   TEXT,
    calificacion_cliente  SMALLINT,              -- la que da el empleado al cliente
    comentario_cliente    TEXT,
    CONSTRAINT pk_asignacion              PRIMARY KEY (id_servicio, id_empleado),
    CONSTRAINT ck_asignacion_calif_empl   CHECK (calificacion_empleado BETWEEN 1 AND 5),
    CONSTRAINT ck_asignacion_calif_client CHECK (calificacion_cliente  BETWEEN 1 AND 5)
);

-- Tipo de servicio N:M Insumo (insumos que necesita cada tipo de servicio)
CREATE TABLE insumo_requerido (
    id_tipo_servicio    INTEGER      NOT NULL,   -- #*
    id_insumo           INTEGER      NOT NULL,   -- #*
    cantidad_sugerida   NUMERIC(8,2) NOT NULL,
    CONSTRAINT pk_insumo_requerido          PRIMARY KEY (id_tipo_servicio, id_insumo),
    CONSTRAINT ck_insumo_requerido_cantidad CHECK (cantidad_sugerida > 0)
);

-- Servicio N:M Insumo (insumos usados en cada servicio)
CREATE TABLE insumo_usado (
    id_servicio         INTEGER      NOT NULL,   -- #*
    id_insumo           INTEGER      NOT NULL,   -- #*
    cantidad            NUMERIC(8,2) NOT NULL,
    proporcionado_por   VARCHAR(10)  NOT NULL DEFAULT 'empresa',
    CONSTRAINT pk_insumo_usado           PRIMARY KEY (id_servicio, id_insumo),
    CONSTRAINT ck_insumo_usado_cantidad  CHECK (cantidad > 0),
    CONSTRAINT ck_insumo_usado_proveedor CHECK (proporcionado_por IN ('empresa', 'cliente'))
);


-- =====================================================================
-- 4. CLAVES FORÁNEAS
-- =====================================================================

-- ---------- Ubicación y viviendas ----------
ALTER TABLE barrio
    ADD CONSTRAINT fk_barrio_zona
    FOREIGN KEY (id_zona) REFERENCES zona (id_zona) ON DELETE RESTRICT;

ALTER TABLE vivienda
    ADD CONSTRAINT fk_vivienda_cliente
    FOREIGN KEY (id_cliente) REFERENCES cliente (id_cliente) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_vivienda_barrio
    FOREIGN KEY (id_barrio) REFERENCES barrio (id_barrio) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_vivienda_tipo_vivienda
    FOREIGN KEY (id_tipo_vivienda) REFERENCES tipo_vivienda (id_tipo_vivienda) ON DELETE RESTRICT;

ALTER TABLE area
    ADD CONSTRAINT fk_area_vivienda
    FOREIGN KEY (id_vivienda) REFERENCES vivienda (id_vivienda) ON DELETE CASCADE,
    ADD CONSTRAINT fk_area_tipo_area
    FOREIGN KEY (id_tipo_area) REFERENCES tipo_area (id_tipo_area) ON DELETE RESTRICT;

ALTER TABLE elemento
    ADD CONSTRAINT fk_elemento_area
    FOREIGN KEY (id_area) REFERENCES area (id_area) ON DELETE CASCADE,
    ADD CONSTRAINT fk_elemento_tipo_elemento
    FOREIGN KEY (id_tipo_elemento) REFERENCES tipo_elemento (id_tipo_elemento) ON DELETE RESTRICT;

-- ---------- Empleados ----------
ALTER TABLE empleado
    ADD CONSTRAINT fk_empleado_supervisor
    FOREIGN KEY (id_supervisor) REFERENCES empleado (id_empleado) ON DELETE SET NULL;

ALTER TABLE empleado_especialidad
    ADD CONSTRAINT fk_empleado_especialidad_empleado
    FOREIGN KEY (id_empleado) REFERENCES empleado (id_empleado) ON DELETE CASCADE,
    ADD CONSTRAINT fk_empleado_especialidad_especialidad
    FOREIGN KEY (id_especialidad) REFERENCES especialidad (id_especialidad) ON DELETE RESTRICT;

ALTER TABLE empleado_zona
    ADD CONSTRAINT fk_empleado_zona_empleado
    FOREIGN KEY (id_empleado) REFERENCES empleado (id_empleado) ON DELETE CASCADE,
    ADD CONSTRAINT fk_empleado_zona_zona
    FOREIGN KEY (id_zona) REFERENCES zona (id_zona) ON DELETE RESTRICT;

-- ---------- Servicios ----------
ALTER TABLE tipo_servicio
    ADD CONSTRAINT fk_tipo_servicio_especialidad
    FOREIGN KEY (id_especialidad) REFERENCES especialidad (id_especialidad) ON DELETE RESTRICT;

ALTER TABLE servicio
    ADD CONSTRAINT fk_servicio_vivienda
    FOREIGN KEY (id_vivienda) REFERENCES vivienda (id_vivienda) ON DELETE RESTRICT;

ALTER TABLE detalle_servicio
    ADD CONSTRAINT fk_detalle_servicio_servicio
    FOREIGN KEY (id_servicio) REFERENCES servicio (id_servicio) ON DELETE CASCADE,
    ADD CONSTRAINT fk_detalle_servicio_tipo_servicio
    FOREIGN KEY (id_tipo_servicio) REFERENCES tipo_servicio (id_tipo_servicio) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_detalle_servicio_area
    FOREIGN KEY (id_area) REFERENCES area (id_area) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_detalle_servicio_elemento
    FOREIGN KEY (id_elemento) REFERENCES elemento (id_elemento) ON DELETE RESTRICT;

ALTER TABLE asignacion
    ADD CONSTRAINT fk_asignacion_servicio
    FOREIGN KEY (id_servicio) REFERENCES servicio (id_servicio) ON DELETE CASCADE,
    ADD CONSTRAINT fk_asignacion_empleado
    FOREIGN KEY (id_empleado) REFERENCES empleado (id_empleado) ON DELETE RESTRICT;

-- ---------- Insumos ----------
ALTER TABLE insumo
    ADD CONSTRAINT fk_insumo_categoria
    FOREIGN KEY (id_categoria) REFERENCES categoria_insumo (id_categoria) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_insumo_proveedor
    FOREIGN KEY (id_proveedor) REFERENCES proveedor (id_proveedor) ON DELETE RESTRICT;

ALTER TABLE insumo_requerido
    ADD CONSTRAINT fk_insumo_requerido_tipo_servicio
    FOREIGN KEY (id_tipo_servicio) REFERENCES tipo_servicio (id_tipo_servicio) ON DELETE CASCADE,
    ADD CONSTRAINT fk_insumo_requerido_insumo
    FOREIGN KEY (id_insumo) REFERENCES insumo (id_insumo) ON DELETE CASCADE;

ALTER TABLE insumo_usado
    ADD CONSTRAINT fk_insumo_usado_servicio
    FOREIGN KEY (id_servicio) REFERENCES servicio (id_servicio) ON DELETE CASCADE,
    ADD CONSTRAINT fk_insumo_usado_insumo
    FOREIGN KEY (id_insumo) REFERENCES insumo (id_insumo) ON DELETE RESTRICT;

-- ---------- Pagos ----------
ALTER TABLE pago
    ADD CONSTRAINT fk_pago_servicio
    FOREIGN KEY (id_servicio) REFERENCES servicio (id_servicio) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_pago_metodo_pago
    FOREIGN KEY (id_metodo_pago) REFERENCES metodo_pago (id_metodo_pago) ON DELETE RESTRICT;


-- =====================================================================
-- 5. RESTRICCIONES ADICIONALES (índices para las FK más consultadas)
-- PostgreSQL no crea índices automáticamente en las columnas FK.
-- =====================================================================

CREATE INDEX ix_barrio_zona              ON barrio (id_zona);
CREATE INDEX ix_vivienda_cliente         ON vivienda (id_cliente);
CREATE INDEX ix_vivienda_barrio          ON vivienda (id_barrio);
CREATE INDEX ix_area_vivienda            ON area (id_vivienda);
CREATE INDEX ix_elemento_area            ON elemento (id_area);
CREATE INDEX ix_empleado_supervisor      ON empleado (id_supervisor);
CREATE INDEX ix_servicio_vivienda        ON servicio (id_vivienda);
CREATE INDEX ix_servicio_fecha           ON servicio (fecha);
CREATE INDEX ix_detalle_servicio_serv    ON detalle_servicio (id_servicio);
CREATE INDEX ix_asignacion_empleado      ON asignacion (id_empleado);
CREATE INDEX ix_insumo_usado_insumo      ON insumo_usado (id_insumo);
CREATE INDEX ix_pago_metodo              ON pago (id_metodo_pago);

-- Fin del script
